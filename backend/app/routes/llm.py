import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class ExplainMatchRequest(BaseModel):
    name_a: str
    name_b: str
    name_similarity: float
    address_similarity: float
    embedding_similarity: float
    country_match: float
    jurisdiction_match: float
    final_score: float
    decision: str
    reason_codes: Optional[List[str]] = []


class VerificationReportRequest(BaseModel):
    lei: str


class QueryParseRequest(BaseModel):
    query: str


@router.post("/explain-match")
def explain_match(req: ExplainMatchRequest):
    try:
        from llm.explain_match import explain_match as _explain
        explanation = _explain(
            name_a=req.name_a,
            name_b=req.name_b,
            name_similarity=req.name_similarity,
            address_similarity=req.address_similarity,
            embedding_similarity=req.embedding_similarity,
            country_match=req.country_match,
            jurisdiction_match=req.jurisdiction_match,
            final_score=req.final_score,
            decision=req.decision,
            reason_codes=req.reason_codes,
        )
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verification-report")
def verification_report(req: VerificationReportRequest):
    from app.services.postgres_service import get_entity_by_lei, get_entity_duplicates
    from app.services.neo4j_service import get_relationship_list

    entity = get_entity_by_lei(req.lei)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    duplicates = get_entity_duplicates(req.lei)
    relationships = get_relationship_list(req.lei)

    try:
        from llm.verification_report import generate_verification_report
        report = generate_verification_report(
            entity=entity,
            duplicates=duplicates,
            graph_relationships=[
                {"type": r.get("rel_type", ""), "target": r.get("target_label", "")}
                for r in relationships
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        import uuid
        from app.db.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("""
            INSERT INTO verification_reports (id, lei, report_text, created_at)
            VALUES (:id, :lei, :report_text, NOW())
        """), {"id": str(uuid.uuid4()), "lei": req.lei, "report_text": report})
        db.commit()
        db.close()
    except Exception:
        pass

    return {"lei": req.lei, "report": report}


@router.post("/parse-query")
def parse_query(req: QueryParseRequest):
    try:
        from llm.query_parser import parse_search_query
        result = parse_search_query(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
