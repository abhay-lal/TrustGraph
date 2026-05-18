import os
from typing import Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

COLLECTION = os.environ.get("QDRANT_COLLECTION", "trustgraph_entities")
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


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
    """Embed query and search Qdrant for nearest matching entities."""
    model = _get_model()
    vector = model.encode(query, normalize_embeddings=True).tolist()
    client = _get_client()

    must = []
    if country:
        must.append(FieldCondition(key="country", match=MatchValue(value=country.upper())))
    if entity_status:
        must.append(FieldCondition(key="entity_status", match=MatchValue(value=entity_status.upper())))

    query_filter = Filter(must=must) if must else None

    try:
        results = client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [{"score": round(r.score, 4), **r.payload} for r in results]
    except Exception as e:
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
