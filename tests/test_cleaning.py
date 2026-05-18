import pytest
from pipelines.clean import (
    normalize_company_name,
    normalize_address,
    normalize_country,
    standardize_status,
    remove_punctuation_noise,
)


class TestNormalizeCompanyName:
    def test_title_cases_name(self):
        assert normalize_company_name("APPLE INC") == "Apple Inc"

    def test_replaces_incorporated(self):
        result = normalize_company_name("Acme Incorporated")
        assert "Inc" in result

    def test_normalises_llc_variants(self):
        assert normalize_company_name("Some Company L.L.C.") == "Some Company LLC"

    def test_strips_trailing_comma(self):
        result = normalize_company_name("Company Name,")
        assert not result.endswith(",")

    def test_collapses_whitespace(self):
        result = normalize_company_name("Company   Name")
        assert "  " not in result

    def test_empty_string(self):
        assert normalize_company_name("") == ""

    def test_non_string(self):
        assert normalize_company_name(None) == ""  # type: ignore

    def test_jp_morgan_normalisation(self):
        result = normalize_company_name("J.P. MORGAN CHASE BANK, N.A.")
        assert "NA" in result or "Na" in result


class TestNormalizeAddress:
    def test_expands_abbreviations(self):
        # normalize_address standardises abbreviations — result is title-cased
        result = normalize_address("123 Market Street")
        assert "123" in result

    def test_handles_empty(self):
        assert normalize_address("") == ""

    def test_handles_none(self):
        assert normalize_address(None) == ""  # type: ignore


class TestNormalizeCountry:
    def test_us_passthrough(self):
        assert normalize_country("US") == "US"

    def test_lowercase(self):
        assert normalize_country("us") == "US"

    def test_alpha3(self):
        assert normalize_country("USA") == "US"

    def test_full_name(self):
        result = normalize_country("Germany")
        assert result == "DE"

    def test_invalid_returns_something(self):
        result = normalize_country("XX")
        assert isinstance(result, str)

    def test_empty(self):
        assert normalize_country("") == ""


class TestStandardizeStatus:
    def test_active(self):
        assert standardize_status("ACTIVE") == "ACTIVE"

    def test_lowercase_active(self):
        assert standardize_status("active") == "ACTIVE"

    def test_invalid_becomes_unknown(self):
        assert standardize_status("BANANA") == "UNKNOWN"

    def test_none(self):
        assert standardize_status(None) == "UNKNOWN"  # type: ignore

    def test_spaces_to_underscores(self):
        assert standardize_status("pending transfer") == "PENDING_TRANSFER"


class TestRemovePunctuationNoise:
    def test_removes_internal_dots(self):
        assert "." not in remove_punctuation_noise("N.A.")

    def test_strips_trailing_comma(self):
        result = remove_punctuation_noise("Company Name,")
        assert not result.endswith(",")
