import pytest
from pipelines.entity_resolution import (
    compare_entities,
    _name_similarity,
    _address_similarity,
    _country_match,
    _jurisdiction_match,
    _decide,
    THRESHOLD_SAME,
    THRESHOLD_REVIEW,
)


class TestNameSimilarity:
    def test_identical_names(self):
        assert _name_similarity("Apple Inc", "Apple Inc") == 1.0

    def test_clear_match(self):
        score = _name_similarity("Apple Inc", "Apple Incorporated")
        assert score > 0.7

    def test_clear_mismatch(self):
        score = _name_similarity("Apple Inc", "Deutsche Bank AG")
        assert score < 0.5

    def test_empty_strings(self):
        assert _name_similarity("", "Apple") == 0.0
        assert _name_similarity("Apple", "") == 0.0


class TestAddressSimilarity:
    def test_identical(self):
        assert _address_similarity("123 Main St", "123 Main St") == 1.0

    def test_abbreviation_variant(self):
        score = _address_similarity("123 Market Street", "123 Market St")
        assert score > 0.7

    def test_empty(self):
        assert _address_similarity("", "123 Main") == 0.0


class TestCountryMatch:
    def test_match(self):
        assert _country_match("US", "US") == 1.0

    def test_no_match(self):
        assert _country_match("US", "DE") == 0.0

    def test_case_insensitive(self):
        assert _country_match("us", "US") == 1.0

    def test_empty(self):
        assert _country_match("", "US") == 0.0


class TestDecide:
    def test_same_entity_threshold(self):
        assert _decide(THRESHOLD_SAME) == "same_entity"
        assert _decide(THRESHOLD_SAME + 0.05) == "same_entity"

    def test_needs_review_threshold(self):
        assert _decide(THRESHOLD_REVIEW) == "needs_review"
        assert _decide(THRESHOLD_REVIEW + 0.05) == "needs_review"

    def test_different_entity(self):
        assert _decide(THRESHOLD_REVIEW - 0.01) == "different_entity"
        assert _decide(0.0) == "different_entity"


class TestCompareEntities:
    def _entity(self, lei, name, address_city="New York", country="US", jurisdiction="Delaware"):
        return {
            "lei": lei,
            "legal_name": name,
            "normalized_name": name,
            "legal_address_line1": "123 Main St",
            "legal_address_city": address_city,
            "country": country,
            "jurisdiction": jurisdiction,
        }

    def test_identical_entities_score_high(self):
        a = self._entity("LEI001", "Apple Inc")
        result = compare_entities(a, a)
        assert result["final_score"] >= THRESHOLD_SAME
        assert result["decision"] == "same_entity"

    def test_different_entities_score_low(self):
        a = self._entity("LEI001", "Apple Inc", country="US")
        b = self._entity("LEI002", "Deutsche Bank AG", address_city="Frankfurt", country="DE", jurisdiction="Germany")
        result = compare_entities(a, b)
        assert result["final_score"] < THRESHOLD_SAME

    def test_result_has_required_keys(self):
        a = self._entity("LEI001", "Acme Inc")
        b = self._entity("LEI002", "Acme Incorporated")
        result = compare_entities(a, b)
        for key in ("id", "lei_a", "lei_b", "final_score", "decision", "reason_codes"):
            assert key in result

    def test_name_abbreviation_match(self):
        a = self._entity("LEI001", "ACME Inc")
        b = self._entity("LEI002", "Acme Incorporated")
        result = compare_entities(a, b)
        assert result["name_similarity"] > 0.7

    def test_embedding_similarity_zero_without_vectors(self):
        a = self._entity("LEI001", "Apple Inc")
        b = self._entity("LEI002", "Apple Incorporated")
        result = compare_entities(a, b)
        assert result["embedding_similarity"] == 0.0
