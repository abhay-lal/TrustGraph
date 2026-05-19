"""
embeddings.py — Generate embeddings for entity text profiles.
Uses OpenAI text-embedding-3-small (fast, lightweight, no local GPU needed).
"""

import logging
import os
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data")) / "processed"
BATCH_SIZE = 100
EMBED_MODEL = "text-embedding-3-small"
VECTOR_SIZE = 1536  # text-embedding-3-small output dimension


def build_text_profile(row: dict) -> str:
    """Create a natural-language text profile from entity fields."""
    name = row.get("legal_name") or row.get("normalized_name") or "Unknown"
    jurisdiction = row.get("jurisdiction") or "unknown jurisdiction"
    country = row.get("country") or "unknown country"
    status = row.get("entity_status") or "unknown status"
    address_parts = filter(None, [
        row.get("legal_address_line1"),
        row.get("legal_address_city"),
        row.get("legal_address_postal"),
    ])
    address = ", ".join(address_parts) or "no address on record"
    return (
        f"{name} is a legal entity registered in {jurisdiction}, "
        f"located in {country}, with status {status}. "
        f"Address: {address}."
    )


def generate_embeddings(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Embed all entities using OpenAI text-embedding-3-small.
    Returns a dict mapping LEI → embedding vector.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    profiles = [build_text_profile(row) for _, row in df.iterrows()]
    leis = df["lei"].tolist()

    logger.info("Generating OpenAI embeddings for %d entities...", len(profiles))

    embeddings = {}
    for i in range(0, len(profiles), BATCH_SIZE):
        batch_profiles = profiles[i:i + BATCH_SIZE]
        batch_leis = leis[i:i + BATCH_SIZE]

        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=batch_profiles,
        )
        for lei, emb_obj in zip(batch_leis, response.data):
            embeddings[lei] = np.array(emb_obj.embedding, dtype=np.float32)

        if i % 1000 == 0:
            logger.info("Embedded %d / %d entities", i + len(batch_profiles), len(profiles))

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
