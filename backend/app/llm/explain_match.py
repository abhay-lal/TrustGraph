"""
explain_match.py — LLM-generated explanations for entity resolution decisions.
"""

import os
from openai import OpenAI
from app.llm.prompts import EXPLAIN_MATCH_SYSTEM, EXPLAIN_MATCH_USER


def explain_match(
    name_a: str,
    name_b: str,
    name_similarity: float,
    address_similarity: float,
    embedding_similarity: float,
    country_match: float,
    jurisdiction_match: float,
    final_score: float,
    decision: str,
    reason_codes: list,
) -> str:
    """Generate a plain-English explanation for an entity resolution decision."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    country_str = "Yes" if country_match >= 1.0 else "No"
    juris_str = "Yes" if jurisdiction_match >= 1.0 else "No"
    codes_str = ", ".join(reason_codes) if reason_codes else "none"

    prompt = EXPLAIN_MATCH_USER.format(
        name_a=name_a,
        name_b=name_b,
        name_similarity=name_similarity,
        address_similarity=address_similarity,
        embedding_similarity=embedding_similarity,
        country_match=country_str,
        jurisdiction_match=juris_str,
        final_score=final_score,
        decision=decision,
        reason_codes=codes_str,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXPLAIN_MATCH_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()
