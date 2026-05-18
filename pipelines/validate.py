"""
validate.py — Data quality checks and report generation.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(os.environ.get("DATA_DIR", "/opt/airflow/data")) / "reports"

VALID_COUNTRIES = {
    "AF", "AL", "DZ", "AD", "AO", "AG", "AR", "AM", "AU", "AT", "AZ", "BS", "BH", "BD",
    "BB", "BY", "BE", "BZ", "BJ", "BT", "BO", "BA", "BW", "BR", "BN", "BG", "BF", "BI",
    "CV", "KH", "CM", "CA", "CF", "TD", "CL", "CN", "CO", "KM", "CG", "CD", "CR", "HR",
    "CU", "CY", "CZ", "DK", "DJ", "DM", "DO", "EC", "EG", "SV", "GQ", "ER", "EE", "SZ",
    "ET", "FJ", "FI", "FR", "GA", "GM", "GE", "DE", "GH", "GR", "GD", "GT", "GN", "GW",
    "GY", "HT", "HN", "HU", "IS", "IN", "ID", "IR", "IQ", "IE", "IL", "IT", "JM", "JP",
    "JO", "KZ", "KE", "KI", "KP", "KR", "KW", "KG", "LA", "LV", "LB", "LS", "LR", "LY",
    "LI", "LT", "LU", "MG", "MW", "MY", "MV", "ML", "MT", "MH", "MR", "MU", "MX", "FM",
    "MD", "MC", "MN", "ME", "MA", "MZ", "MM", "NA", "NR", "NP", "NL", "NZ", "NI", "NE",
    "NG", "NO", "OM", "PK", "PW", "PA", "PG", "PY", "PE", "PH", "PL", "PT", "QA", "RO",
    "RU", "RW", "KN", "LC", "VC", "WS", "SM", "ST", "SA", "SN", "RS", "SC", "SL", "SG",
    "SK", "SI", "SB", "SO", "ZA", "SS", "ES", "LK", "SD", "SR", "SE", "CH", "SY", "TW",
    "TJ", "TZ", "TH", "TL", "TG", "TO", "TT", "TN", "TR", "TM", "TV", "UG", "UA", "AE",
    "GB", "US", "UY", "UZ", "VU", "VE", "VN", "YE", "ZM", "ZW",
}

VALID_ENTITY_STATUSES = {"ACTIVE", "INACTIVE", "MERGED", "RETIRED", "ANNULLED", "DUPLICATE",
                         "TRANSFERRED", "PENDING_TRANSFER", "PENDING_ARCHIVAL"}


def run_quality_checks(df: pd.DataFrame, start_time: float = None) -> dict:
    """Run all data quality checks and return a metrics dict."""
    if start_time is None:
        start_time = time.time()

    total = len(df)
    if total == 0:
        return {"total_records": 0, "data_quality_score": 0.0}

    checks = {}

    # Null checks
    missing_lei = df["lei"].isna().sum() if "lei" in df.columns else total
    missing_name = df["legal_name"].isna().sum() if "legal_name" in df.columns else total
    missing_address = df["legal_address_line1"].isna().sum() if "legal_address_line1" in df.columns else 0

    # Duplicate LEI
    dup_lei = df["lei"].duplicated().sum() if "lei" in df.columns else 0

    # Invalid country
    if "country" in df.columns:
        invalid_country = (~df["country"].isin(VALID_COUNTRIES) & df["country"].notna()).sum()
    else:
        invalid_country = 0

    # Invalid entity status
    if "entity_status" in df.columns:
        invalid_status = (~df["entity_status"].isin(VALID_ENTITY_STATUSES) & df["entity_status"].notna()).sum()
    else:
        invalid_status = 0

    # Validity score: a record is "valid" if it has LEI, name, and valid country
    valid_mask = pd.Series([True] * total, index=df.index)
    if "lei" in df.columns:
        valid_mask &= df["lei"].notna()
    if "legal_name" in df.columns:
        valid_mask &= df["legal_name"].notna() & (df["legal_name"].str.strip() != "")
    if "country" in df.columns:
        valid_mask &= df["country"].isin(VALID_COUNTRIES) | df["country"].isna()

    valid_records = int(valid_mask.sum())
    invalid_records = total - valid_records

    runtime = round(time.time() - start_time, 2)
    quality_score = round((valid_records / total) * 100, 2) if total > 0 else 0.0

    checks["run_date"] = datetime.utcnow().isoformat()
    checks["total_records"] = total
    checks["valid_records"] = valid_records
    checks["invalid_records"] = invalid_records
    checks["missing_lei_count"] = int(missing_lei)
    checks["missing_name_count"] = int(missing_name)
    checks["missing_name_rate"] = round(missing_name / total, 4)
    checks["missing_address_rate"] = round(missing_address / total, 4)
    checks["duplicate_lei_count"] = int(dup_lei)
    checks["invalid_country_count"] = int(invalid_country)
    checks["invalid_status_count"] = int(invalid_status)
    checks["pipeline_runtime_seconds"] = runtime
    checks["data_quality_score"] = quality_score

    checks["check_results"] = {
        "lei_not_null": missing_lei == 0,
        "legal_name_not_null": missing_name == 0,
        "no_duplicate_lei": dup_lei == 0,
        "country_valid_rate_above_95pct": (1 - invalid_country / total) >= 0.95,
        "missing_address_below_30pct": (missing_address / total) <= 0.30,
    }

    return checks


def save_quality_report(metrics: dict, run_id: str = None) -> str:
    """Save quality metrics to a JSON report file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"data_quality_report_{run_id or 'latest'}.json"
    path = REPORTS_DIR / filename
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    latest_path = REPORTS_DIR / "data_quality_report.json"
    with open(latest_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    logger.info("Data quality report saved to %s", path)
    return str(path)
