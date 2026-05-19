"""
verification_report.py — LLM-generated analyst verification reports.
"""

import os
from openai import OpenAI
from app.llm.prompts import VERIFICATION_REPORT_SYSTEM, VERIFICATION_REPORT_USER


def generate_verification_report(
    entity: dict,
    duplicates: list = None,
    graph_relationships: list = None,
    quality_issues: list = None,
    risk_matches: list = None,
) -> str:
    """Generate a full verification report for a legal entity."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _fmt_list(items, default="None identified"):
        if not items:
            return default
        return "\n".join(f"- {item}" for item in items)

    dup_text = _fmt_list(
        [f"{d.get('name_b', d.get('lei_b', ''))} (score: {d.get('final_score', 0):.2f})"
         for d in (duplicates or [])]
    )
    graph_text = _fmt_list(
        [f"{r.get('type', 'related')} → {r.get('target', '')}"
         for r in (graph_relationships or [])]
    )
    quality_text = _fmt_list(quality_issues)
    risk_text = _fmt_list(
        [f"{r.get('name', '')} ({r.get('dataset', '')}, confidence: {r.get('score', 0):.2f})"
         for r in (risk_matches or [])]
    )

    legal_address = entity.get("legal_address", "")
    if isinstance(legal_address, dict):
        legal_address = ", ".join(filter(None, legal_address.values()))

    prompt = VERIFICATION_REPORT_USER.format(
        legal_name=entity.get("legal_name", ""),
        lei=entity.get("lei", ""),
        country=entity.get("country", ""),
        jurisdiction=entity.get("jurisdiction", ""),
        entity_status=entity.get("entity_status", ""),
        registration_status=entity.get("registration_status", ""),
        legal_address=legal_address,
        managing_lou=entity.get("managing_lou", ""),
        duplicates=dup_text,
        graph_relationships=graph_text,
        quality_issues=quality_text,
        risk_matches=risk_text,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VERIFICATION_REPORT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    return response.choices[0].message.content.strip()
