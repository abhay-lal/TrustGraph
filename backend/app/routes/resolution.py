import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from app.services import postgres_service

router = APIRouter()


class CompareRequest(BaseModel):
    lei_a: str
    lei_b: str


class ReviewDecisionRequest(BaseModel):
    match_id: str
    decision: str  # accepted | rejected


@router.get("/matches")
def get_matches(
    decision: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    return postgres_service.get_resolution_matches(
        decision=decision, limit=limit, offset=offset
    )


@router.post("/compare")
def compare_entities(req: CompareRequest):
    from pipelines.entity_resolution import compare_entities as _compare

    entity_a = postgres_service.get_entity_by_lei(req.lei_a)
    entity_b = postgres_service.get_entity_by_lei(req.lei_b)

    if not entity_a:
        raise HTTPException(status_code=404, detail=f"Entity {req.lei_a} not found")
    if not entity_b:
        raise HTTPException(status_code=404, detail=f"Entity {req.lei_b} not found")

    result = _compare(entity_a, entity_b)
    if isinstance(result.get("reason_codes"), str):
        try:
            result["reason_codes"] = json.loads(result["reason_codes"])
        except Exception:
            pass
    return result


@router.post("/review")
def review_match(req: ReviewDecisionRequest):
    if req.decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'accepted' or 'rejected'")
    ok = postgres_service.update_reviewer_decision(req.match_id, req.decision)
    if not ok:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"status": "updated", "match_id": req.match_id, "decision": req.decision}
