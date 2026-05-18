"""
embeddings.py — Generate sentence embeddings for entity text profiles.
"""

import logging
import os
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data")) / "processed"
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 256


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
    Embed all entities using Sentence Transformers.
    Returns a dict mapping LEI → embedding vector.
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    profiles = [build_text_profile(row) for _, row in df.iterrows()]
    leis = df["lei"].tolist()

    logger.info("Generating embeddings for %d entities...", len(profiles))
    vectors = model.encode(
        profiles,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    embeddings = {lei: vec for lei, vec in zip(leis, vectors)}

    out_path = PROCESSED_DIR / "embeddings.npz"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
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
