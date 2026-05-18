"""
test_api.py — FastAPI endpoint tests using TestClient.
Requires a running PostgreSQL connection or uses a mocked service layer.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("app.db.database.create_engine"), \
         patch("app.db.database.SessionLocal"):
        from app.main import app
        return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestEntities:
    def test_search_returns_list(self, client):
        mock_entities = [
            {
                "lei": "LEI001", "legal_name": "Apple Inc", "country": "US",
                "entity_status": "ACTIVE", "normalized_name": "Apple Inc",
            }
        ]
        with patch("app.services.postgres_service.search_entities", return_value=mock_entities):
            res = client.get("/entities/search?query=apple")
            assert res.status_code == 200
            data = res.json()
            assert isinstance(data, list)
            assert data[0]["lei"] == "LEI001"

    def test_get_entity_found(self, client):
        mock_entity = {"lei": "LEI001", "legal_name": "Apple Inc", "country": "US"}
        with patch("app.services.postgres_service.get_entity_by_lei", return_value=mock_entity):
            res = client.get("/entities/LEI001")
            assert res.status_code == 200
            assert res.json()["lei"] == "LEI001"

    def test_get_entity_not_found(self, client):
        with patch("app.services.postgres_service.get_entity_by_lei", return_value=None):
            res = client.get("/entities/NONEXISTENT")
            assert res.status_code == 404

    def test_get_entity_duplicates(self, client):
        with patch("app.services.postgres_service.get_entity_duplicates", return_value=[]):
            res = client.get("/entities/LEI001/duplicates")
            assert res.status_code == 200
            assert isinstance(res.json(), list)


class TestResolution:
    def test_get_matches(self, client):
        with patch("app.services.postgres_service.get_resolution_matches", return_value=[]):
            res = client.get("/entity-resolution/matches")
            assert res.status_code == 200
            assert isinstance(res.json(), list)

    def test_compare_entities(self, client):
        entity_a = {
            "lei": "LEI001", "legal_name": "Apple Inc", "normalized_name": "Apple Inc",
            "country": "US", "jurisdiction": "Delaware",
            "legal_address_line1": "1 Apple Park", "legal_address_city": "Cupertino",
        }
        entity_b = {
            "lei": "LEI002", "legal_name": "Apple Incorporated", "normalized_name": "Apple Incorporated",
            "country": "US", "jurisdiction": "Delaware",
            "legal_address_line1": "1 Apple Park", "legal_address_city": "Cupertino",
        }
        with patch("app.services.postgres_service.get_entity_by_lei", side_effect=[entity_a, entity_b]):
            res = client.post(
                "/entity-resolution/compare",
                json={"lei_a": "LEI001", "lei_b": "LEI002"},
            )
            assert res.status_code == 200
            data = res.json()
            assert "final_score" in data
            assert "decision" in data
            assert data["final_score"] >= 0.0


class TestSemanticSearch:
    def test_semantic_search_returns_results(self, client):
        mock_results = [{"lei": "LEI001", "legal_name": "Apple Inc", "score": 0.92}]
        with patch("app.services.qdrant_service.semantic_search", return_value=mock_results):
            res = client.post(
                "/semantic-search",
                json={"query": "technology companies US", "limit": 5},
            )
            assert res.status_code == 200
            data = res.json()
            assert "results" in data


class TestPipeline:
    def test_pipeline_stats(self, client):
        mock_stats = {
            "total_entities": 50000,
            "active_entities": 45000,
            "duplicate_matches": 2000,
            "needs_review": 500,
            "data_quality_score": 96.5,
            "last_pipeline_run": "2024-01-01T00:00:00",
            "vector_index_size": 48000,
        }
        with patch("app.services.postgres_service.get_pipeline_stats", return_value=mock_stats), \
             patch("app.services.qdrant_service.get_collection_stats", return_value={"vector_count": 48000}):
            res = client.get("/pipeline/stats")
            assert res.status_code == 200
            data = res.json()
            assert "total_entities" in data
