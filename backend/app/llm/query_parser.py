"""
query_parser.py — Parse natural-language search queries into structured filters.
"""

import json
import os
from openai import OpenAI
from app.llm.prompts import QUERY_PARSER_SYSTEM, QUERY_PARSER_USER


def parse_search_query(query: str) -> dict:
    """
    Convert a natural-language query into semantic + filter parameters.

    Returns:
        {
          "semantic_query": str,
          "filters": {"country": str, "entity_status": str, "jurisdiction": str}
        }
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    prompt = QUERY_PARSER_USER.format(query=query)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": QUERY_PARSER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"semantic_query": query, "filters": {}}

    parsed.setdefault("semantic_query", query)
    parsed.setdefault("filters", {})
    return parsed
