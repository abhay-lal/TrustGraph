"""
load_qdrant.py — Index entity embeddings into Qdrant for semantic search.
"""

import logging
import os
import uuid
from typing import Dict

import numpy as np
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

logger = logging.getLogger(__name__)

COLLECTION = os.environ.get("QDRANT_COLLECTION", "trustgraph_entities")
VECTOR_SIZE = 1536  # text-embedding-3-small output dimension
BATCH_SIZE = 256


def _get_client() -> QdrantClient:
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", 6333))
    return QdrantClient(host=host, port=port)


def _ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", COLLECTION)


def load_embeddings_to_qdrant(
    df: pd.DataFrame, embeddings: Dict[str, np.ndarray]
) -> int:
    """Upload entity embeddings and metadata to Qdrant."""
    client = _get_client()
    _ensure_collection(client)

    points = []
    for _, row in df.iterrows():
        lei = row.get("lei")
        vec = embeddings.get(lei)
        if vec is None or str(lei).startswith("SYNTH_"):
            continue

        payload = {
            "lei": lei,
            "legal_name": row.get("legal_name", ""),
            "normalized_name": row.get("normalized_name", ""),
            "country": row.get("country", ""),
            "jurisdiction": row.get("jurisdiction", ""),
            "entity_status": row.get("entity_status", ""),
        }
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, lei))
        points.append(PointStruct(id=point_id, vector=vec.tolist(), payload=payload))

    total = 0
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION, points=batch)
        total += len(batch)

    logger.info("Indexed %d vectors into Qdrant.", total)
    return total


def semantic_search(
    query_vector: np.ndarray,
    limit: int = 10,
    country: str = None,
    entity_status: str = None,
) -> list:
    """Search Qdrant for nearest neighbours with optional metadata filters."""
    client = _get_client()

    must = []
    if country:
        must.append(FieldCondition(key="country", match=MatchValue(value=country.upper())))
    if entity_status:
        must.append(FieldCondition(key="entity_status", match=MatchValue(value=entity_status.upper())))

    query_filter = Filter(must=must) if must else None

    response = client.query_points(
        collection_name=COLLECTION,
        query=query_vector.tolist(),
        limit=limit,
        query_filter=query_filter,
        with_payload=True,
    )
    return [{"score": r.score, **r.payload} for r in response.points]
