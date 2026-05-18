"""
prompts.py — All LLM prompt templates for TrustGraph.
"""

EXPLAIN_MATCH_SYSTEM = """You are an expert data analyst specializing in legal entity identity resolution.
Your task is to explain in 2-3 clear sentences why two company records either match or don't match.
Be specific about which signals drove the decision. Do not hedge excessively."""

EXPLAIN_MATCH_USER = """Two legal entity records were compared with the following similarity scores:

Record A: {name_a}
Record B: {name_b}

Scores:
- Name similarity:      {name_similarity:.2f}
- Address similarity:   {address_similarity:.2f}
- Embedding similarity: {embedding_similarity:.2f}
- Country match:        {country_match}
- Jurisdiction match:   {jurisdiction_match}
- Final score:          {final_score:.2f}
- Decision:             {decision}
- Reason codes:         {reason_codes}

Explain this decision concisely."""


VERIFICATION_REPORT_SYSTEM = """You are a compliance analyst generating structured verification reports for legal entities.
Write a concise but complete report. Use plain language. Format each section clearly."""

VERIFICATION_REPORT_USER = """Generate a verification report for this legal entity:

Company: {legal_name}
LEI: {lei}
Country: {country}
Jurisdiction: {jurisdiction}
Status: {entity_status}
Registration Status: {registration_status}
Address: {legal_address}
Managing LOU: {managing_lou}

Known duplicate candidates:
{duplicates}

Graph relationships:
{graph_relationships}

Data quality issues:
{quality_issues}

Risk/watchlist matches:
{risk_matches}

Write a report with these sections:
1. Company Summary
2. Registration & Status
3. Known Duplicate Candidates
4. Corporate Relationships
5. Data Quality Notes
6. Risk Flags
7. Recommended Analyst Action"""


QUERY_PARSER_SYSTEM = """You are a search query parser for a legal entity database.
Convert the user's natural language query into structured search parameters.
Always respond with valid JSON only, no explanation."""

QUERY_PARSER_USER = """Parse this search query into structured parameters:

Query: "{query}"

Return JSON with these fields (omit fields that are not mentioned or implied):
{{
  "semantic_query": "keywords for semantic/vector search",
  "filters": {{
    "country": "ISO 2-letter code if mentioned",
    "entity_status": "ACTIVE or INACTIVE if mentioned",
    "jurisdiction": "jurisdiction name if mentioned"
  }}
}}"""
