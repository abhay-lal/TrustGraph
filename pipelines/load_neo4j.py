"""
load_neo4j.py — Load entity nodes and relationships into Neo4j.
"""

import logging
import os
from typing import List

import pandas as pd
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


def _get_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "trustgraph")
    return GraphDatabase.driver(uri, auth=(user, password))


def _create_constraints(session):
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.lei IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Address) REQUIRE a.address_id IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country) REQUIRE c.code IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (j:Jurisdiction) REQUIRE j.code IS UNIQUE")


def load_entities_to_neo4j(df: pd.DataFrame) -> None:
    """Create Company nodes and related Country/Jurisdiction/Address nodes."""
    driver = _get_driver()
    batch_size = 500

    with driver.session() as session:
        _create_constraints(session)

    rows = df.to_dict(orient="records")
    batches = [rows[i:i + batch_size] for i in range(0, len(rows), batch_size)]

    with driver.session() as session:
        for batch in batches:
            session.run("""
                UNWIND $rows AS row
                MERGE (c:Company {lei: row.lei})
                SET c.legal_name     = row.legal_name,
                    c.normalized_name = row.normalized_name,
                    c.entity_status  = row.entity_status,
                    c.registration_status = row.registration_status,
                    c.source         = row.source

                FOREACH (_ IN CASE WHEN row.country IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (co:Country {code: row.country})
                    MERGE (c)-[:LOCATED_IN]->(co)
                )
                FOREACH (_ IN CASE WHEN row.jurisdiction IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (j:Jurisdiction {code: row.jurisdiction})
                    MERGE (c)-[:REGISTERED_IN]->(j)
                )
            """, rows=batch)

    logger.info("Loaded %d companies into Neo4j.", len(rows))
    driver.close()


def load_resolution_matches_to_neo4j(matches_df: pd.DataFrame) -> None:
    """Create MATCHED_TO relationships between entity pairs."""
    if matches_df.empty:
        return

    driver = _get_driver()
    rows = matches_df[matches_df["decision"].isin(["same_entity", "needs_review"])].to_dict(
        orient="records"
    )

    with driver.session() as session:
        session.run("""
            UNWIND $rows AS row
            MATCH (a:Company {lei: row.lei_a})
            MATCH (b:Company {lei: row.lei_b})
            MERGE (a)-[r:MATCHED_TO]->(b)
            SET r.final_score = row.final_score,
                r.decision    = row.decision
        """, rows=rows)

    logger.info("Loaded %d MATCHED_TO relationships into Neo4j.", len(rows))
    driver.close()


def load_gleif_level2(relationships: List[dict]) -> None:
    """
    Load GLEIF Level 2 parent/subsidiary relationships.
    Each dict should have: lei, parent_lei, relationship_type (DIRECT|ULTIMATE)
    """
    if not relationships:
        return

    driver = _get_driver()
    with driver.session() as session:
        session.run("""
            UNWIND $rows AS row
            MATCH (child:Company {lei: row.lei})
            MATCH (parent:Company {lei: row.parent_lei})
            FOREACH (_ IN CASE WHEN row.relationship_type = 'DIRECT' THEN [1] ELSE [] END |
                MERGE (child)-[:HAS_DIRECT_PARENT]->(parent)
            )
            FOREACH (_ IN CASE WHEN row.relationship_type = 'ULTIMATE' THEN [1] ELSE [] END |
                MERGE (child)-[:HAS_ULTIMATE_PARENT]->(parent)
            )
        """, rows=relationships)

    logger.info("Loaded %d Level 2 relationships.", len(relationships))
    driver.close()
