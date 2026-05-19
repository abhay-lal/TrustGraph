#!/bin/bash
# run_local.sh — start the TrustGraph backend locally (assumes Postgres/Neo4j/Qdrant are running)

export POSTGRES_USER=trustgraph
export POSTGRES_PASSWORD=trustgraph
export POSTGRES_DB=trustgraph
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=trustgraph
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export QDRANT_COLLECTION=trustgraph_entities
export OPENAI_API_KEY=${OPENAI_API_KEY:-"sk-..."}
export OPENAI_MODEL=gpt-4o-mini
export PYTHONPATH="$(pwd)"

export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://trustgraph:trustgraph@localhost/trustgraph"
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__LOAD_EXAMPLES=false
export AIRFLOW_HOME="$(pwd)/.airflow"

echo "Starting FastAPI on http://localhost:8000 ..."
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
