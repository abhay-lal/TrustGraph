import json
import os
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import SessionLocal


def _db() -> Session:
    return SessionLocal()


def search_entities(
    query: str = None,
    country: str = None,
    jurisdiction: str = None,
    entity_status: str = None,
    limit: int = 20,
    offset: int = 0,
) -> list:
    db = _db()
    try:
        conditions = ["1=1"]
        params = {"limit": limit, "offset": offset}

        if query:
            conditions.append(
                "(normalized_name ILIKE :query OR lei ILIKE :query OR legal_name ILIKE :query)"
            )
            params["query"] = f"%{query}%"
        if country:
            conditions.append("country = :country")
            params["country"] = country.upper()
        if jurisdiction:
            conditions.append("jurisdiction ILIKE :jurisdiction")
            params["jurisdiction"] = f"%{jurisdiction}%"
        if entity_status:
            conditions.append("entity_status = :entity_status")
            params["entity_status"] = entity_status.upper()

        where = " AND ".join(conditions)
        sql = text(f"""
            SELECT id, lei, legal_name, normalized_name, country, jurisdiction,
                   entity_status, registration_status, legal_address,
                   headquarters_address, managing_lou, source, created_at
            FROM entities
            WHERE {where}
            ORDER BY legal_name
            LIMIT :limit OFFSET :offset
        """)
        result = db.execute(sql, params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_entity_by_lei(lei: str) -> Optional[dict]:
    db = _db()
    try:
        result = db.execute(
            text("SELECT * FROM entities WHERE lei = :lei"), {"lei": lei}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    finally:
        db.close()


def get_entity_duplicates(lei: str) -> list:
    db = _db()
    try:
        result = db.execute(text("""
            SELECT * FROM entity_resolution_matches
            WHERE (lei_a = :lei OR lei_b = :lei)
              AND decision IN ('same_entity', 'needs_review')
            ORDER BY final_score DESC
            LIMIT 20
        """), {"lei": lei})
        return [dict(r) for r in result.mappings().all()]
    finally:
        db.close()


def get_resolution_matches(decision: str = None, limit: int = 50, offset: int = 0) -> list:
    db = _db()
    try:
        params = {"limit": limit, "offset": offset}
        cond = "1=1"
        if decision:
            cond = "decision = :decision"
            params["decision"] = decision
        result = db.execute(text(f"""
            SELECT * FROM entity_resolution_matches
            WHERE {cond}
            ORDER BY final_score DESC
            LIMIT :limit OFFSET :offset
        """), params)
        return [dict(r) for r in result.mappings().all()]
    finally:
        db.close()


def update_reviewer_decision(match_id: str, reviewer_decision: str) -> bool:
    db = _db()
    try:
        db.execute(text("""
            UPDATE entity_resolution_matches
            SET reviewer_decision = :decision, reviewed_at = NOW()
            WHERE id = :id
        """), {"id": match_id, "decision": reviewer_decision})
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def get_latest_quality_run() -> Optional[dict]:
    db = _db()
    try:
        result = db.execute(text("""
            SELECT * FROM data_quality_runs ORDER BY run_date DESC LIMIT 1
        """))
        row = result.mappings().first()
        return dict(row) if row else None
    finally:
        db.close()


def get_pipeline_stats() -> dict:
    db = _db()
    try:
        total = db.execute(text("SELECT COUNT(*) FROM entities")).scalar() or 0
        active = db.execute(
            text("SELECT COUNT(*) FROM entities WHERE entity_status = 'ACTIVE'")
        ).scalar() or 0
        matches = db.execute(
            text("SELECT COUNT(*) FROM entity_resolution_matches WHERE decision = 'same_entity'")
        ).scalar() or 0
        needs_review = db.execute(
            text("SELECT COUNT(*) FROM entity_resolution_matches WHERE decision = 'needs_review'")
        ).scalar() or 0
        quality = db.execute(
            text("SELECT data_quality_score, run_date FROM data_quality_runs ORDER BY run_date DESC LIMIT 1")
        ).mappings().first()

        return {
            "total_entities": total,
            "active_entities": active,
            "duplicate_matches": matches,
            "needs_review": needs_review,
            "data_quality_score": float(quality["data_quality_score"]) if quality else None,
            "last_pipeline_run": str(quality["run_date"]) if quality else None,
        }
    finally:
        db.close()
