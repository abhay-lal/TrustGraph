"""
load_postgres.py — Upsert cleaned entities and resolution matches into PostgreSQL.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def _get_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@"
        f"{os.environ.get('POSTGRES_HOST', 'localhost')}/"
        f"{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url, pool_pre_ping=True)


def load_entities(df: pd.DataFrame) -> int:
    """Upsert entity records into the entities table."""
    engine = _get_engine()

    _ensure_tables(engine)

    rows = []
    for _, row in df.iterrows():
        lei = row.get("lei")
        if not lei or str(lei).startswith("SYNTH_"):
            continue

        legal_address = json.dumps({
            "line1": row.get("legal_address_line1"),
            "city": row.get("legal_address_city"),
            "postal": row.get("legal_address_postal"),
        })
        hq_address = json.dumps({
            "line1": row.get("hq_address_line1"),
            "city": row.get("hq_address_city"),
        })

        rows.append({
            "id": str(lei),
            "lei": str(lei),
            "legal_name": row.get("legal_name") or "",
            "normalized_name": row.get("normalized_name") or "",
            "country": row.get("country"),
            "jurisdiction": row.get("jurisdiction"),
            "entity_status": row.get("entity_status"),
            "registration_status": row.get("registration_status"),
            "legal_address": legal_address,
            "headquarters_address": hq_address,
            "managing_lou": row.get("managing_lou"),
            "source": row.get("source", "GLEIF"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

    if not rows:
        return 0

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO entities (
                id, lei, legal_name, normalized_name, country, jurisdiction,
                entity_status, registration_status, legal_address,
                headquarters_address, managing_lou, source, created_at, updated_at
            ) VALUES (
                :id, :lei, :legal_name, :normalized_name, :country, :jurisdiction,
                :entity_status, :registration_status, :legal_address,
                :headquarters_address, :managing_lou, :source, :created_at, :updated_at
            )
            ON CONFLICT (lei) DO UPDATE SET
                legal_name = EXCLUDED.legal_name,
                normalized_name = EXCLUDED.normalized_name,
                entity_status = EXCLUDED.entity_status,
                registration_status = EXCLUDED.registration_status,
                legal_address = EXCLUDED.legal_address,
                headquarters_address = EXCLUDED.headquarters_address,
                updated_at = EXCLUDED.updated_at
        """), rows)

    logger.info("Upserted %d entities into PostgreSQL.", len(rows))
    return len(rows)


def load_resolution_matches(matches_df: pd.DataFrame) -> int:
    """Insert entity resolution results into entity_resolution_matches table."""
    engine = _get_engine()
    if matches_df.empty:
        return 0

    rows = matches_df.to_dict(orient="records")
    for r in rows:
        if not r.get("id"):
            r["id"] = str(uuid.uuid4())
        r["created_at"] = datetime.utcnow()

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO entity_resolution_matches (
                id, lei_a, lei_b, name_a, name_b,
                name_similarity, address_similarity, embedding_similarity,
                country_match, jurisdiction_match, final_score,
                decision, reason_codes, created_at
            ) VALUES (
                :id, :lei_a, :lei_b, :name_a, :name_b,
                :name_similarity, :address_similarity, :embedding_similarity,
                :country_match, :jurisdiction_match, :final_score,
                :decision, :reason_codes, :created_at
            )
            ON CONFLICT (id) DO NOTHING
        """), rows)

    logger.info("Inserted %d resolution matches.", len(rows))
    return len(rows)


def save_quality_run(metrics: dict) -> None:
    """Persist a data quality run record."""
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO data_quality_runs (
                id, run_date, total_records, valid_records, invalid_records,
                missing_name_rate, missing_address_rate, duplicate_lei_count,
                pipeline_runtime_seconds, data_quality_score
            ) VALUES (
                :id, :run_date, :total_records, :valid_records, :invalid_records,
                :missing_name_rate, :missing_address_rate, :duplicate_lei_count,
                :pipeline_runtime_seconds, :data_quality_score
            )
        """), {
            "id": str(uuid.uuid4()),
            "run_date": datetime.utcnow(),
            "total_records": str(metrics.get("total_records", 0)),
            "valid_records": str(metrics.get("valid_records", 0)),
            "invalid_records": str(metrics.get("invalid_records", 0)),
            "missing_name_rate": str(metrics.get("missing_name_rate", 0)),
            "missing_address_rate": str(metrics.get("missing_address_rate", 0)),
            "duplicate_lei_count": str(metrics.get("duplicate_lei_count", 0)),
            "pipeline_runtime_seconds": str(metrics.get("pipeline_runtime_seconds", 0)),
            "data_quality_score": str(metrics.get("data_quality_score", 0)),
        })


def _ensure_tables(engine) -> None:
    """Create tables if they don't exist (idempotent)."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS entities (
                id VARCHAR PRIMARY KEY,
                lei VARCHAR(50) UNIQUE NOT NULL,
                legal_name VARCHAR(512) NOT NULL,
                normalized_name VARCHAR(512),
                other_names TEXT,
                country VARCHAR(3),
                jurisdiction VARCHAR(128),
                entity_status VARCHAR(64),
                registration_status VARCHAR(64),
                legal_address TEXT,
                headquarters_address TEXT,
                managing_lou VARCHAR(128),
                source VARCHAR(64) DEFAULT 'GLEIF',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS entity_resolution_matches (
                id VARCHAR PRIMARY KEY,
                lei_a VARCHAR(50),
                lei_b VARCHAR(50),
                name_a VARCHAR(512),
                name_b VARCHAR(512),
                name_similarity FLOAT,
                address_similarity FLOAT,
                embedding_similarity FLOAT,
                country_match FLOAT,
                jurisdiction_match FLOAT,
                final_score FLOAT NOT NULL,
                decision VARCHAR(32) NOT NULL,
                reason_codes TEXT,
                reviewer_decision VARCHAR(32),
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS data_quality_runs (
                id VARCHAR PRIMARY KEY,
                run_date TIMESTAMP DEFAULT NOW(),
                total_records VARCHAR,
                valid_records VARCHAR,
                invalid_records VARCHAR,
                missing_name_rate VARCHAR,
                missing_address_rate VARCHAR,
                duplicate_lei_count VARCHAR,
                pipeline_runtime_seconds VARCHAR,
                data_quality_score VARCHAR,
                report_path VARCHAR
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS verification_reports (
                id VARCHAR PRIMARY KEY,
                lei VARCHAR(20) NOT NULL,
                report_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
