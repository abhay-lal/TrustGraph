import os
from neo4j import GraphDatabase


def _driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "trustgraph")
    return GraphDatabase.driver(uri, auth=(user, password))


def get_entity_graph(lei: str) -> dict:
    """Return nodes and edges for a company's immediate neighbourhood."""
    driver = _driver()
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company {lei: $lei})
                OPTIONAL MATCH (c)-[r1]->(related)
                OPTIONAL MATCH (other)-[r2]->(c)
                RETURN c,
                       collect(DISTINCT {type: type(r1), target: related}) AS outgoing,
                       collect(DISTINCT {type: type(r2), source: other}) AS incoming
            """, lei=lei)
            record = result.single()
            if not record:
                return {"nodes": [], "edges": []}

            company = dict(record["c"])
            nodes = [{"id": lei, "label": company.get("legal_name", lei), "type": "Company"}]
            edges = []

            for rel in record["outgoing"]:
                if rel["target"]:
                    target = dict(rel["target"])
                    target_id = target.get("lei") or target.get("code") or target.get("address_id", "")
                    target_label = target.get("legal_name") or target.get("code", target_id)
                    target_type = list(rel["target"].labels)[0] if hasattr(rel["target"], "labels") else "Node"
                    nodes.append({"id": target_id, "label": target_label, "type": target_type})
                    edges.append({"source": lei, "target": target_id, "type": rel["type"]})

            for rel in record["incoming"]:
                if rel["source"]:
                    src = dict(rel["source"])
                    src_id = src.get("lei", "")
                    src_label = src.get("legal_name", src_id)
                    nodes.append({"id": src_id, "label": src_label, "type": "Company"})
                    edges.append({"source": src_id, "target": lei, "type": rel["type"]})

            unique_nodes = {n["id"]: n for n in nodes if n["id"]}.values()
            return {"nodes": list(unique_nodes), "edges": edges}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}
    finally:
        driver.close()


def get_relationship_list(lei: str) -> list:
    """Return a flat list of relationships for display in the UI."""
    driver = _driver()
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company {lei: $lei})-[r]->(n)
                RETURN type(r) AS rel_type,
                       COALESCE(n.legal_name, n.code, n.address_id, '') AS target_label,
                       COALESCE(n.lei, '') AS target_lei,
                       labels(n)[0] AS target_type
            """, lei=lei)
            return [dict(r) for r in result]
    except Exception:
        return []
    finally:
        driver.close()
