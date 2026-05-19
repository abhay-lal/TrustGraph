import os
from typing import Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

COLLECTION = os.environ.get("QDRANT_COLLECTION", "trustgraph_entities")
EMBED_MODEL = "text-embedding-3-small"


def _embed(text: str) -> list:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(model=EMBED_MODEL, input=[text])
    return response.data[0].embedding


def _get_client() -> QdrantClient:
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", 6333))
    return QdrantClient(host=host, port=port)


def semantic_search(
    query: str,
    limit: int = 10,
    country: str = None,
    entity_status: str = None,
) -> list:
    """Embed query with OpenAI and search Qdrant for nearest matching entities."""
    try:
        vector = _embed(query)
    except Exception as e:
        return []

    client = _get_client()

    must = []
    if country:
        must.append(FieldCondition(key="country", match=MatchValue(value=country.upper())))
    if entity_status:
        must.append(FieldCondition(key="entity_status", match=MatchValue(value=entity_status.upper())))

    query_filter = Filter(must=must) if must else None

    try:
        response = client.query_points(
            collection_name=COLLECTION,
            query=vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [{"score": round(r.score, 4), **r.payload} for r in response.points]
    except Exception:
        return []


def get_collection_stats() -> dict:
    client = _get_client()
    try:
        info = client.get_collection(COLLECTION)
        return {
            "vector_count": info.points_count,
            "collection": COLLECTION,
        }
    except Exception:
        return {"vector_count": 0, "collection": COLLECTION}
