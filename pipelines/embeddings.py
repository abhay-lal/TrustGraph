"""
embeddings.py — Generate embeddings for entity text profiles.
Uses OpenAI text-embedding-3-small (fast, lightweight, no local GPU needed).
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data")) / "processed"
BATCH_SIZE = 50           # ~2 500 tokens/batch  → safe under 40 k TPM
EMBED_MODEL = "text-embedding-3-small"
VECTOR_SIZE = 1536        # text-embedding-3-small output dimension
INTER_BATCH_SLEEP = 4.0   # seconds between batches to stay under rate limit


def build_text_profile(row: dict) -> str:
    """Create a natural-language text profile from entity fields."""
    name = row.get("legal_name") or row.get("normalized_name") or "Unknown"
    jurisdiction = row.get("jurisdiction") or "unknown jurisdiction"
    country = row.get("country") or "unknown country"
    status = row.get("entity_status") or "unknown status"
    address_parts = [
        str(v) for v in [
            row.get("legal_address_line1"),
            row.get("legal_address_city"),
            row.get("legal_address_postal"),
        ]
        if v is not None and str(v) not in ("nan", "None", "")
    ]
    address = ", ".join(address_parts) or "no address on record"
    return (
        f"{name} is a legal entity registered in {jurisdiction}, "
        f"located in {country}, with status {status}. "
        f"Address: {address}."
    )


def _embed_batch_with_retry(client, profiles: list, max_retries: int = 5) -> list:
    """Call OpenAI embeddings with exponential back-off on rate-limit errors."""
    from openai import RateLimitError
    delay = 15.0
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(model=EMBED_MODEL, input=profiles)
            return [obj.embedding for obj in response.data]
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            logger.warning(
                "Rate limit hit, waiting %.0fs before retry %d/%d …",
                delay, attempt + 1, max_retries,
            )
            time.sleep(delay)
            delay *= 2  # exponential back-off


def generate_embeddings(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Embed all entities using OpenAI text-embedding-3-small.
    Returns a dict mapping LEI → embedding vector.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    profiles = [build_text_profile(row) for _, row in df.iterrows()]
    leis = df["lei"].tolist()

    logger.info("Generating OpenAI embeddings for %d entities (batch=%d) …",
                len(profiles), BATCH_SIZE)

    embeddings = {}
    total_batches = (len(profiles) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_num, i in enumerate(range(0, len(profiles), BATCH_SIZE)):
        batch_profiles = profiles[i : i + BATCH_SIZE]
        batch_leis = leis[i : i + BATCH_SIZE]

        vectors = _embed_batch_with_retry(client, batch_profiles)
        for lei, vec in zip(batch_leis, vectors):
            embeddings[lei] = np.array(vec, dtype=np.float32)

        logger.info("Embedded batch %d/%d  (%d total so far)",
                    batch_num + 1, total_batches, i + len(batch_profiles))

        # Throttle — stay well under the 40 k TPM free-tier limit
        if i + BATCH_SIZE < len(profiles):
            time.sleep(INTER_BATCH_SLEEP)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "embeddings.npz"
    np.savez_compressed(str(out_path), **{
        lei.replace("/", "_"): vec for lei, vec in embeddings.items()
    })
    logger.info("Embeddings saved to %s", out_path)
    return embeddings


def load_embeddings() -> Dict[str, np.ndarray]:
    """Load pre-computed embeddings from disk."""
    path = PROCESSED_DIR / "embeddings.npz"
    if not path.exists():
        logger.warning("No embeddings file found at %s", path)
        return {}
    data = np.load(str(path))
    return {k.replace("_", "/"): data[k] for k in data.files}
