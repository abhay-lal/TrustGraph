"""
extract.py — Download GLEIF LEI golden copy, sample records,
load OpenSanctions, and generate synthetic duplicates.
"""

import io
import json
import logging
import os
import random
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

RAW_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data")) / "raw"
SAMPLE_SIZE = int(os.environ.get("GLEIF_SAMPLE_SIZE", 50_000))

GLEIF_GOLDEN_COPY_URL = (
    "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest"
)

NOISE_SUFFIXES = {
    "Inc.": ["Inc", "Incorporated", "INC"],
    "Corp.": ["Corp", "Corporation", "CORP"],
    "Ltd.": ["Ltd", "Limited", "LTD"],
    "LLC": ["L.L.C.", "L.L.C", "Llc"],
    "N.A.": ["NA", "N.A", "National Association"],
    "Co.": ["Co", "Company", "CO"],
}

ABBREVIATIONS = {
    "Street": "St.",
    "Avenue": "Ave.",
    "Boulevard": "Blvd.",
    "Drive": "Dr.",
    "Road": "Rd.",
    "North": "N.",
    "South": "S.",
    "East": "E.",
    "West": "W.",
}

TYPO_MAP = {
    "a": "aa",
    "e": "ee",
    "i": "ii",
    "o": "oo",
    "n": "m",
    "m": "n",
}


# ── GLEIF ─────────────────────────────────────────────────────────────────────

def _resolve_gleif_download_url() -> str:
    """Resolve the actual CSV download URL from the GLEIF API."""
    resp = requests.get(GLEIF_GOLDEN_COPY_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for file_info in data.get("data", {}).get("attributes", {}).get("fullFiles", []):
        if file_info.get("mimeType") == "text/csv":
            return file_info["url"]
    raise ValueError("Could not find CSV download URL from GLEIF golden copy API")


def extract_gleif_records() -> pd.DataFrame:
    """Download and sample GLEIF LEI golden copy records."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "gleif_entities.csv"

    if out_path.exists():
        logger.info("GLEIF raw file already exists, skipping download.")
        df = pd.read_csv(out_path, low_memory=False)
        return df

    logger.info("Resolving GLEIF download URL...")
    try:
        download_url = _resolve_gleif_download_url()
    except Exception as exc:
        logger.warning("Could not resolve GLEIF URL (%s), using fallback sample.", exc)
        return _generate_gleif_fallback_sample()

    logger.info("Downloading GLEIF golden copy from %s", download_url)
    resp = requests.get(download_url, stream=True, timeout=120)
    resp.raise_for_status()

    content = io.BytesIO(resp.content)

    if download_url.endswith(".zip"):
        with zipfile.ZipFile(content) as zf:
            csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
            with zf.open(csv_name) as f:
                df = pd.read_csv(f, low_memory=False)
    else:
        df = pd.read_csv(content, low_memory=False)

    df = _normalise_gleif_columns(df)
    df = df.sample(min(SAMPLE_SIZE, len(df)), random_state=42).reset_index(drop=True)
    df.to_csv(out_path, index=False)
    logger.info("Saved %d GLEIF records to %s", len(df), out_path)
    return df


def _normalise_gleif_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename GLEIF column names to internal schema."""
    rename = {
        "LEI": "lei",
        "Entity.LegalName": "legal_name",
        "Entity.OtherEntityNames": "other_names",
        "Entity.LegalAddress.FirstAddressLine": "legal_address_line1",
        "Entity.LegalAddress.City": "legal_address_city",
        "Entity.LegalAddress.Country": "country",
        "Entity.LegalAddress.PostalCode": "legal_address_postal",
        "Entity.HeadquartersAddress.FirstAddressLine": "hq_address_line1",
        "Entity.HeadquartersAddress.City": "hq_address_city",
        "Entity.HeadquartersAddress.Country": "hq_country",
        "Entity.LegalJurisdiction": "jurisdiction",
        "Entity.EntityStatus": "entity_status",
        "Registration.InitialRegistrationDate": "initial_registration_date",
        "Registration.LastUpdateDate": "last_update_date",
        "Registration.RegistrationStatus": "registration_status",
        "Registration.ManagingLOU": "managing_lou",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    keep = list(rename.values())
    df = df[[c for c in keep if c in df.columns]]
    return df


def _generate_gleif_fallback_sample() -> pd.DataFrame:
    """Return a small synthetic sample when GLEIF is unreachable."""
    sample_entities = [
        {"lei": f"LEI{i:018d}", "legal_name": f"Sample Company {i} Inc.", "country": "US",
         "jurisdiction": "Delaware", "entity_status": "ACTIVE", "registration_status": "ISSUED"}
        for i in range(1, 1001)
    ]
    df = pd.DataFrame(sample_entities)
    out_path = RAW_DIR / "gleif_entities.csv"
    df.to_csv(out_path, index=False)
    return df


# ── OpenSanctions ──────────────────────────────────────────────────────────────

def extract_opensanctions_records() -> pd.DataFrame:
    """Download OpenSanctions consolidated dataset (FtM JSON lines)."""
    out_path = RAW_DIR / "opensanctions_entities.csv"
    if out_path.exists():
        logger.info("OpenSanctions file already exists, skipping.")
        return pd.read_csv(out_path)

    url = "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json"
    logger.info("Downloading OpenSanctions from %s", url)

    records = []
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("schema") in ("Company", "Organization", "LegalEntity"):
                props = obj.get("properties", {})
                records.append({
                    "os_id": obj.get("id"),
                    "os_name": (props.get("name") or [""])[0],
                    "os_country": (props.get("country") or [""])[0],
                    "os_schema": obj.get("schema"),
                    "os_datasets": ",".join(obj.get("datasets", [])),
                })
            if len(records) >= 20_000:
                break
    except Exception as exc:
        logger.warning("OpenSanctions download failed: %s — using empty set.", exc)

    df = pd.DataFrame(records) if records else pd.DataFrame(
        columns=["os_id", "os_name", "os_country", "os_schema", "os_datasets"]
    )
    df.to_csv(out_path, index=False)
    logger.info("Saved %d OpenSanctions records.", len(df))
    return df


# ── Synthetic Duplicates ───────────────────────────────────────────────────────

def _apply_noise(name: str) -> str:
    """Apply random noise to a company name to simulate a duplicate."""
    noise_type = random.choice(["suffix", "abbrev", "typo", "case", "punct"])

    if noise_type == "suffix":
        for suffix, alts in NOISE_SUFFIXES.items():
            if suffix in name:
                return name.replace(suffix, random.choice(alts), 1)

    if noise_type == "abbrev":
        for word, abbr in ABBREVIATIONS.items():
            if word in name:
                return name.replace(word, abbr, 1)

    if noise_type == "typo" and len(name) > 4:
        idx = random.randint(1, len(name) - 2)
        char = name[idx].lower()
        replacement = TYPO_MAP.get(char, char + char)
        return name[:idx] + replacement + name[idx + 1:]

    if noise_type == "case":
        return name.upper() if random.random() > 0.5 else name.lower()

    if noise_type == "punct":
        return re.sub(r"[,.]", "", name)

    return name + " LLC" if not name.endswith("LLC") else name.rstrip(" LLC")


def generate_synthetic_duplicates(gleif_df: pd.DataFrame) -> pd.DataFrame:
    """Create noisy duplicate records from a sample of GLEIF entities."""
    out_path = RAW_DIR / "synthetic_duplicates.csv"
    if out_path.exists():
        return pd.read_csv(out_path)

    sample = gleif_df.dropna(subset=["legal_name"]).sample(
        min(5_000, len(gleif_df)), random_state=99
    )

    dupes = []
    for _, row in sample.iterrows():
        noisy_name = _apply_noise(str(row["legal_name"]))
        dupe = row.to_dict()
        dupe["lei"] = "SYNTH_" + str(row.get("lei", ""))
        dupe["legal_name"] = noisy_name
        dupe["source"] = "synthetic"
        dupes.append(dupe)

    df = pd.DataFrame(dupes)
    df.to_csv(out_path, index=False)
    logger.info("Generated %d synthetic duplicates.", len(df))
    return df
