from fastapi import APIRouter, Query, HTTPException
from app.services import postgres_service, neo4j_service

router = APIRouter()


@router.get("/search")
def search_entities(
    query: str = Query(None),
    country: str = Query(None),
    jurisdiction: str = Query(None),
    entity_status: str = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    return postgres_service.search_entities(
        query=query,
        country=country,
        jurisdiction=jurisdiction,
        entity_status=entity_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{lei}")
def get_entity(lei: str):
    entity = postgres_service.get_entity_by_lei(lei)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/{lei}/graph")
def get_entity_graph(lei: str):
    return neo4j_service.get_entity_graph(lei)


@router.get("/{lei}/relationships")
def get_entity_relationships(lei: str):
    return neo4j_service.get_relationship_list(lei)


@router.get("/{lei}/duplicates")
def get_entity_duplicates(lei: str):
    return postgres_service.get_entity_duplicates(lei)
