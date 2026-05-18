"""
clean.py — Normalize company names, addresses, countries, and statuses.
"""

import re
import unicodedata

import pandas as pd
import pycountry

# ── Constants ─────────────────────────────────────────────────────────────────

LEGAL_SUFFIX_MAP = {
    r"\bincorporated\b": "Inc",
    r"\binc\.\b": "Inc",
    r"\bcorporation\b": "Corp",
    r"\bcorp\.\b": "Corp",
    r"\blimited\b": "Ltd",
    r"\bltd\.\b": "Ltd",
    r"\bl\.l\.c\.?\b": "LLC",
    r"\bn\.a\.?\b": "NA",
    r"\bplc\b": "PLC",
    r"\bgmbh\b": "GmbH",
    r"\bag\b": "AG",
    r"\bs\.a\.\b": "SA",
    r"\bb\.v\.\b": "BV",
    r"\bn\.v\.\b": "NV",
    r"\bco\.\b": "Co",
    r"\bcompany\b": "Co",
}

ADDRESS_ABBREV = {
    r"\bstreet\b": "St",
    r"\bavenue\b": "Ave",
    r"\bboulevard\b": "Blvd",
    r"\bdrive\b": "Dr",
    r"\broad\b": "Rd",
    r"\bsuite\b": "Ste",
    r"\bfloor\b": "Fl",
    r"\bnorth\b": "N",
    r"\bsouth\b": "S",
    r"\beast\b": "E",
    r"\bwest\b": "W",
}

VALID_STATUSES = {
    "ACTIVE", "INACTIVE", "MERGED", "RETIRED", "ANNULLED",
    "DUPLICATE", "TRANSFERRED", "PENDING_TRANSFER", "PENDING_ARCHIVAL",
}

VALID_REG_STATUSES = {
    "ISSUED", "LAPSED", "MERGED", "RETIRED", "ANNULLED",
    "DUPLICATE", "TRANSFERRED", "PENDING_TRANSFER", "PENDING_ARCHIVAL",
    "PENDING_VALIDATION",
}


# ── Name Normalization ─────────────────────────────────────────────────────────

def normalize_company_name(name: str) -> str:
    """
    Normalize a legal company name:
    - Unicode → ASCII
    - Title case
    - Standardize legal suffixes
    - Remove extra punctuation/whitespace
    """
    if not name or not isinstance(name, str):
        return ""

    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.strip()
    name = name.title()

    for pattern, replacement in LEGAL_SUFFIX_MAP.items():
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

    name = re.sub(r"[,]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def remove_punctuation_noise(text: str) -> str:
    """Remove periods and commas used as noise in names."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"(?<=[A-Za-z])\.(?=[A-Za-z])", "", text)
    text = re.sub(r",\s*$", "", text)
    return text.strip()


# ── Address Normalization ──────────────────────────────────────────────────────

def normalize_address(address: str) -> str:
    """Standardize address abbreviations and casing."""
    if not address or not isinstance(address, str):
        return ""

    address = address.strip().title()

    for pattern, replacement in ADDRESS_ABBREV.items():
        address = re.sub(pattern, replacement, address, flags=re.IGNORECASE)

    address = re.sub(r"\s+", " ", address).strip()
    return address


# ── Country Normalization ──────────────────────────────────────────────────────

def normalize_country(country: str) -> str:
    """
    Normalize country to ISO 3166-1 alpha-2 code.
    Accepts codes, names, and common variants.
    """
    if not country or not isinstance(country, str):
        return ""

    country = country.strip().upper()

    if len(country) == 2:
        try:
            pycountry.countries.get(alpha_2=country)
            return country
        except Exception:
            pass

    if len(country) == 3:
        try:
            c = pycountry.countries.get(alpha_3=country)
            if c:
                return c.alpha_2
        except Exception:
            pass

    try:
        results = pycountry.countries.search_fuzzy(country.title())
        if results:
            return results[0].alpha_2
    except Exception:
        pass

    return country[:2]


# ── Status Normalization ───────────────────────────────────────────────────────

def standardize_status(status: str, valid_set: set = VALID_STATUSES) -> str:
    """Uppercase and validate entity/registration status."""
    if not status or not isinstance(status, str):
        return "UNKNOWN"
    normalized = status.strip().upper().replace(" ", "_").replace("-", "_")
    return normalized if normalized in valid_set else "UNKNOWN"


# ── Full DataFrame Cleaning ────────────────────────────────────────────────────

def clean_entities(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all normalization steps to a raw entities DataFrame."""
    df = df.copy()

    if "legal_name" in df.columns:
        df["normalized_name"] = df["legal_name"].apply(normalize_company_name)

    addr_cols = [c for c in ["legal_address_line1", "hq_address_line1"] if c in df.columns]
    for col in addr_cols:
        df[col] = df[col].apply(normalize_address)

    if "country" in df.columns:
        df["country"] = df["country"].apply(normalize_country)

    if "hq_country" in df.columns:
        df["hq_country"] = df["hq_country"].apply(normalize_country)

    if "entity_status" in df.columns:
        df["entity_status"] = df["entity_status"].apply(standardize_status)

    if "registration_status" in df.columns:
        df["registration_status"] = df["registration_status"].apply(
            lambda s: standardize_status(s, VALID_REG_STATUSES)
        )

    for col in ["legal_name", "normalized_name"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()

    df = df.drop_duplicates(subset=["lei"], keep="first") if "lei" in df.columns else df
    return df
