# TrustGraph

**An end-to-end identity data platform for legal entity verification.**

TrustGraph ingests 50,000+ GLEIF legal entity records through an Airflow pipeline, validates and normalizes them, resolves duplicate companies using fuzzy matching and vector embeddings, models corporate ownership in Neo4j, enables natural-language semantic search via Qdrant, and surfaces an LLM-powered analyst assistant for match explanations and verification reports.

![Stack](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![Airflow](https://img.shields.io/badge/Airflow-2.9-017CEE?style=flat-square&logo=apacheairflow)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql)
![Neo4j](https://img.shields.io/badge/Neo4j-5-008CC1?style=flat-square&logo=neo4j)
![Qdrant](https://img.shields.io/badge/Qdrant-latest-red?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)

---

## What It Does

| Capability | How |
|---|---|
| **Data ingestion** | Airflow DAG downloads GLEIF LEI golden copy, OpenSanctions entities, generates synthetic duplicates |
| **Data cleaning** | Normalizes company names, addresses, country codes, and status fields |
| **Data quality** | Automated checks with pass/fail metrics stored in PostgreSQL and shown in the dashboard |
| **Entity resolution** | Hybrid scoring — RapidFuzz (name + address) + sentence-transformers (semantic embeddings) |
| **Graph modeling** | Neo4j stores parent/subsidiary relationships and resolution matches as a traversable graph |
| **Semantic search** | Natural-language queries parsed by LLM, executed against Qdrant vector index |
| **LLM assistant** | OpenAI `gpt-4o-mini` generates match explanations, verification reports, and query parsing |
| **REST API** | FastAPI with 16 endpoints — entity lookup, resolution, semantic search, LLM, pipeline stats |
| **UI** | Next.js dashboard with pipeline metrics, entity search, interactive graph viz, and ER review |

---

## Architecture

```
GLEIF (50k records) + OpenSanctions + Synthetic Duplicates
                          │
                    Airflow ETL DAG
                          │
           ┌──────────────┼──────────────┐
        Extract        Clean          Validate
                          │
           ┌──────────────┼──────────────┐
        Embed        Entity          Load
     (MiniLM-L6)   Resolution       DBs
                          │
         ┌────────────────┼────────────────┐
    PostgreSQL          Neo4j           Qdrant
   (structured)        (graph)          (vectors)
                          │
                    FastAPI Backend
                          │
               LLM Layer (gpt-4o-mini)
                          │
                   Next.js Frontend
```

---

## Tech Stack

**Backend**
- Python 3.11, FastAPI, SQLAlchemy, Pydantic
- Apache Airflow 2.9 (LocalExecutor)

**Databases**
- PostgreSQL 16 — structured entity records, quality runs, resolution matches
- Neo4j 5 — corporate relationship graph (APOC enabled)
- Qdrant — dense vector index for semantic search

**ML / Search**
- `sentence-transformers` (`all-MiniLM-L6-v2`) for entity profile embeddings
- RapidFuzz for name and address fuzzy matching
- Weighted hybrid scoring with configurable thresholds

**LLM**
- OpenAI `gpt-4o-mini` for match explanation, verification reports, and NL query parsing
- Structured JSON output via function calling for the query parser

**Frontend**
- Next.js 14 (App Router), Tailwind CSS
- `react-force-graph-2d` for interactive graph visualization

**Infra**
- Docker Compose (6 services, health checks, volume mounts)

---

## Features

### Entity Resolution Engine

Duplicate detection using a weighted similarity score across 5 signals:

```
final_score =  0.35 × name_similarity
             + 0.25 × address_similarity
             + 0.20 × embedding_similarity
             + 0.10 × country_match
             + 0.10 × jurisdiction_match
```

| Score | Decision |
|---|---|
| ≥ 0.85 | `same_entity` |
| 0.65 – 0.85 | `needs_review` |
| < 0.65 | `different_entity` |

### Semantic Search

Each company is embedded as a natural-language profile:

```
"Apple Inc is a legal entity registered in Delaware, located in US,
with status ACTIVE. Address: 1 Apple Park Way, Cupertino."
```

Natural-language queries are parsed by the LLM into structured `{semantic_query, filters}` JSON before hitting Qdrant — so a query like *"active fintech companies in Germany"* becomes a vector search with a `country=DE, entity_status=ACTIVE` filter applied.

### LLM-Assisted Analyst Workflow

- **Match explanation** — given two records and their similarity scores, generates a plain-English explanation of why they match or don't
- **Verification report** — structured analyst report covering company summary, registration status, duplicate candidates, corporate relationships, data quality notes, risk flags, and recommended action
- **Query parser** — converts free-text search to structured query parameters

### Corporate Graph (Neo4j)

```cypher
(Company)-[:HAS_DIRECT_PARENT]->(Company)
(Company)-[:HAS_ULTIMATE_PARENT]->(Company)
(Company)-[:REGISTERED_IN]->(Jurisdiction)
(Company)-[:LOCATED_IN]->(Country)
(Company)-[:MATCHED_TO {final_score, decision}]->(Company)
```

Visualized interactively in the UI and fully explorable in the Neo4j Browser.

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone and configure

```bash
git clone https://github.com/your-username/trustgraph.git
cd trustgraph
cp .env.example .env
```

Open `.env` and fill in two values:

```bash
# 1. Your OpenAI API key
OPENAI_API_KEY=sk-proj-...

# 2. A generated Fernet key for Airflow
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
AIRFLOW__CORE__FERNET_KEY=<paste output here>
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| UI (Next.js) | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Airflow | http://localhost:8080 — `admin` / `admin` |
| Neo4j Browser | http://localhost:7474 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

### 3. Run the pipeline

1. Open Airflow at http://localhost:8080
2. Enable and trigger the `trustgraph_etl` DAG
3. Watch the 9-task pipeline run end-to-end (~15–30 min first run for download + embedding)
4. Open the UI at http://localhost:3000 — the dashboard will populate with live metrics

---

## API Reference

```
GET  /health
GET  /entities/search?query=&country=&entity_status=
GET  /entities/{lei}
GET  /entities/{lei}/graph
GET  /entities/{lei}/relationships
GET  /entities/{lei}/duplicates
GET  /entity-resolution/matches?decision=
POST /entity-resolution/compare
POST /entity-resolution/review
POST /semantic-search
GET  /semantic-search/stats
POST /llm/explain-match
POST /llm/verification-report
POST /llm/parse-query
GET  /pipeline/stats
GET  /pipeline/data-quality/latest
```

Full interactive docs: http://localhost:8000/docs

---

## Running Tests

```bash
pip install fastapi sqlalchemy psycopg2-binary rapidfuzz pycountry sentence-transformers openai pytest httpx
pytest
```

Tests cover:
- `test_cleaning.py` — normalization functions (name, address, country, status)
- `test_entity_resolution.py` — scoring logic, thresholds, decision rules
- `test_api.py` — all FastAPI endpoints with mocked service layer

---

## Project Structure

```
trustgraph/
├── docker-compose.yml
├── .env.example
│
├── dags/
│   └── trustgraph_etl_dag.py       # Airflow DAG (9 tasks)
│
├── pipelines/
│   ├── extract.py                  # GLEIF + OpenSanctions + synthetic duplicates
│   ├── clean.py                    # Name, address, country, status normalization
│   ├── validate.py                 # Data quality checks + JSON report
│   ├── entity_resolution.py        # RapidFuzz + weighted scoring engine
│   ├── embeddings.py               # Sentence-transformers text profiles
│   ├── load_postgres.py            # Upsert to PostgreSQL
│   ├── load_neo4j.py               # Graph node/relationship loading
│   └── load_qdrant.py              # Vector index upsert
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── routes/                 # entities, resolution, semantic, llm, pipeline
│       ├── services/               # postgres_service, neo4j_service, qdrant_service
│       ├── models/                 # SQLAlchemy ORM
│       └── db/database.py
│
├── llm/
│   ├── prompts.py
│   ├── explain_match.py
│   ├── verification_report.py
│   └── query_parser.py
│
├── frontend/
│   └── app/
│       ├── page.tsx                # Pipeline dashboard
│       ├── entities/page.tsx       # Search + profile + graph
│       └── resolution/page.tsx     # Side-by-side ER review
│
└── tests/
    ├── test_cleaning.py
    ├── test_entity_resolution.py
    └── test_api.py
```

---

## Skills Demonstrated

`Python` · `FastAPI` · `Apache Airflow` · `PostgreSQL` · `Neo4j` · `Qdrant` · `Docker Compose` · `Data Modeling` · `ETL Pipelines` · `Data Validation` · `Entity Resolution` · `Fuzzy Matching` · `Vector Embeddings` · `Semantic Search` · `Graph Modeling` · `LLM Integration` · `OpenAI API` · `Next.js` · `TypeScript` · `REST API Design`

---

## Dataset Sources

- [GLEIF LEI Golden Copy](https://www.gleif.org/en/lei-data/gleif-golden-copy/download-the-golden-copy) — 50k legal entity records (LEI, name, address, jurisdiction, status)
- [GLEIF Level 2 Data](https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom) — parent/subsidiary ownership relationships
- [OpenSanctions](https://www.opensanctions.org/datasets/) — sanctions and watchlist entities for risk matching
- Synthetic duplicates — programmatically generated noisy copies of GLEIF records for entity resolution testing
