from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services import qdrant_service

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    country: Optional[str] = None
    entity_status: Optional[str] = None
    use_llm_parser: bool = False


@router.post("")
def semantic_search(req: SemanticSearchRequest):
    query = req.query
    filters = {}

    if req.use_llm_parser:
        try:
            from llm.query_parser import parse_search_query
            parsed = parse_search_query(req.query)
            query = parsed.get("semantic_query", req.query)
            filters = parsed.get("filters", {})
        except Exception:
            pass

    country = req.country or filters.get("country")
    status = req.entity_status or filters.get("entity_status")

    results = qdrant_service.semantic_search(
        query=query,
        limit=req.limit,
        country=country,
        entity_status=status,
    )
    return {"query": query, "filters": filters, "results": results}


@router.get("/stats")
def qdrant_stats():
    return qdrant_service.get_collection_stats()
