"""
entity_resolution.py — Hybrid duplicate detection using RapidFuzz + embeddings.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data")) / "processed"

# Scoring weights
W_NAME = 0.35
W_ADDRESS = 0.25
W_EMBEDDING = 0.20
W_COUNTRY = 0.10
W_JURISDICTION = 0.10

# Decision thresholds
THRESHOLD_SAME = 0.85
THRESHOLD_REVIEW = 0.65


def _name_similarity(a: str, b: str) -> float:
    """Weighted combination of token sort ratio and partial ratio."""
    if not a or not b:
        return 0.0
    token_sort = fuzz.token_sort_ratio(a, b) / 100.0
    partial = fuzz.partial_ratio(a, b) / 100.0
    return round(0.6 * token_sort + 0.4 * partial, 4)


def _address_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return round(fuzz.token_set_ratio(a, b) / 100.0, 4)


def _country_match(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return 1.0 if str(a).strip().upper() == str(b).strip().upper() else 0.0


def _jurisdiction_match(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return 1.0 if str(a).strip().upper() == str(b).strip().upper() else 0.0


def _decide(score: float) -> str:
    if score >= THRESHOLD_SAME:
        return "same_entity"
    if score >= THRESHOLD_REVIEW:
        return "needs_review"
    return "different_entity"


def _reason_codes(name_sim: float, addr_sim: float, emb_sim: float,
                  country: float, jurisdiction: float) -> List[str]:
    codes = []
    if name_sim >= 0.85:
        codes.append("similar_name")
    if addr_sim >= 0.80:
        codes.append("similar_address")
    if emb_sim >= 0.85:
        codes.append("similar_embedding")
    if country == 1.0:
        codes.append("same_country")
    if jurisdiction == 1.0:
        codes.append("same_jurisdiction")
    return codes


def compare_entities(row_a: dict, row_b: dict,
                     emb_a: np.ndarray = None,
                     emb_b: np.ndarray = None) -> dict:
    """Compare two entity records and return a resolution result dict."""
    name_sim = _name_similarity(
        row_a.get("normalized_name", ""), row_b.get("normalized_name", "")
    )
    addr_a = " ".join(filter(None, [
        row_a.get("legal_address_line1", ""), row_a.get("legal_address_city", "")
    ]))
    addr_b = " ".join(filter(None, [
        row_b.get("legal_address_line1", ""), row_b.get("legal_address_city", "")
    ]))
    addr_sim = _address_similarity(addr_a, addr_b)
    country = _country_match(row_a.get("country", ""), row_b.get("country", ""))
    juris = _jurisdiction_match(row_a.get("jurisdiction", ""), row_b.get("jurisdiction", ""))

    if emb_a is not None and emb_b is not None:
        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)
        emb_sim = float(np.dot(emb_a, emb_b) / (norm_a * norm_b + 1e-9))
        emb_sim = max(0.0, round(emb_sim, 4))
    else:
        emb_sim = 0.0

    final_score = round(
        W_NAME * name_sim
        + W_ADDRESS * addr_sim
        + W_EMBEDDING * emb_sim
        + W_COUNTRY * country
        + W_JURISDICTION * juris,
        4,
    )

    return {
        "id": str(uuid.uuid4()),
        "lei_a": row_a.get("lei", ""),
        "lei_b": row_b.get("lei", ""),
        "name_a": row_a.get("legal_name", ""),
        "name_b": row_b.get("legal_name", ""),
        "name_similarity": name_sim,
        "address_similarity": addr_sim,
        "embedding_similarity": emb_sim,
        "country_match": country,
        "jurisdiction_match": juris,
        "final_score": final_score,
        "decision": _decide(final_score),
        "reason_codes": json.dumps(_reason_codes(name_sim, addr_sim, emb_sim, country, juris)),
    }


def run_entity_resolution(
    gleif_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    embeddings: dict = None,
) -> pd.DataFrame:
    """
    Match synthetic duplicates against the real GLEIF records.
    Returns a DataFrame of candidate pairs.
    """
    results = []
    gleif_by_lei = {row["lei"]: row for _, row in gleif_df.iterrows()}

    for _, syn_row in synthetic_df.iterrows():
        original_lei = str(syn_row.get("lei", "")).replace("SYNTH_", "")
        if original_lei not in gleif_by_lei:
            continue

        real_row = gleif_by_lei[original_lei]
        emb_real = embeddings.get(original_lei) if embeddings else None
        emb_syn = embeddings.get(syn_row["lei"]) if embeddings else None

        result = compare_entities(
            real_row.to_dict(), syn_row.to_dict(), emb_real, emb_syn
        )
        results.append(result)

    df = pd.DataFrame(results)
    out_path = PROCESSED_DIR / "entity_resolution_matches.csv"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    logger.info("Resolved %d candidate pairs.", len(df))
    return df
