"""
trustgraph_etl_dag.py — Airflow DAG orchestrating the full TrustGraph pipeline.
"""

import time
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "trustgraph",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

dag = DAG(
    "trustgraph_etl",
    default_args=default_args,
    description="TrustGraph: GLEIF ingestion, cleaning, entity resolution, and indexing",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["trustgraph", "etl", "entity-resolution"],
)


# ── Task Functions ─────────────────────────────────────────────────────────────

def task_extract_gleif(**ctx):
    from pipelines.extract import extract_gleif_records
    df = extract_gleif_records()
    ctx["ti"].xcom_push(key="gleif_row_count", value=len(df))
    return len(df)


def task_extract_opensanctions(**ctx):
    from pipelines.extract import extract_opensanctions_records
    df = extract_opensanctions_records()
    ctx["ti"].xcom_push(key="os_row_count", value=len(df))
    return len(df)


def task_clean(**ctx):
    import pandas as pd
    from pathlib import Path
    import os
    from pipelines.extract import extract_gleif_records, generate_synthetic_duplicates
    from pipelines.clean import clean_entities

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    gleif_df = extract_gleif_records()
    clean_df = clean_entities(gleif_df)

    out_path = data_dir / "processed" / "clean_entities.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(out_path, index=False)

    # Also clean + save synthetic duplicates
    syn_df = generate_synthetic_duplicates(gleif_df)
    clean_syn = clean_entities(syn_df)
    syn_path = data_dir / "processed" / "clean_synthetic.csv"
    clean_syn.to_csv(syn_path, index=False)

    ctx["ti"].xcom_push(key="clean_row_count", value=len(clean_df))
    return len(clean_df)


def task_validate(**ctx):
    import pandas as pd
    import time
    import uuid
    from pathlib import Path
    import os
    from pipelines.validate import run_quality_checks, save_quality_report

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    clean_path = data_dir / "processed" / "clean_entities.csv"
    df = pd.read_csv(clean_path, low_memory=False)

    start = time.time()
    metrics = run_quality_checks(df, start_time=start)
    run_id = ctx["run_id"].replace(":", "_").replace("+", "_")
    save_quality_report(metrics, run_id=run_id)

    try:
        from pipelines.load_postgres import save_quality_run
        save_quality_run(metrics)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Could not save quality run to DB: %s", e)

    ctx["ti"].xcom_push(key="data_quality_score", value=metrics.get("data_quality_score"))
    return metrics


def task_embed(**ctx):
    import pandas as pd
    from pathlib import Path
    import os
    from pipelines.embeddings import generate_embeddings

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    clean_path = data_dir / "processed" / "clean_entities.csv"
    df = pd.read_csv(clean_path, low_memory=False)
    embeddings = generate_embeddings(df)
    ctx["ti"].xcom_push(key="embedding_count", value=len(embeddings))
    return len(embeddings)


def task_entity_resolution(**ctx):
    import pandas as pd
    from pathlib import Path
    import os
    from pipelines.entity_resolution import run_entity_resolution
    from pipelines.embeddings import load_embeddings

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    gleif_df = pd.read_csv(data_dir / "processed" / "clean_entities.csv", low_memory=False)
    syn_df = pd.read_csv(data_dir / "processed" / "clean_synthetic.csv", low_memory=False)
    embeddings = load_embeddings()

    matches_df = run_entity_resolution(gleif_df, syn_df, embeddings=embeddings)
    ctx["ti"].xcom_push(key="match_count", value=len(matches_df))
    return len(matches_df)


def task_load_postgres(**ctx):
    import pandas as pd
    from pathlib import Path
    import os
    from pipelines.load_postgres import load_entities, load_resolution_matches

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    entities_df = pd.read_csv(data_dir / "processed" / "clean_entities.csv", low_memory=False)
    count = load_entities(entities_df)

    matches_path = data_dir / "processed" / "entity_resolution_matches.csv"
    if matches_path.exists():
        matches_df = pd.read_csv(matches_path)
        load_resolution_matches(matches_df)

    ctx["ti"].xcom_push(key="postgres_loaded", value=count)
    return count


def task_load_neo4j(**ctx):
    import pandas as pd
    from pathlib import Path
    import os
    from pipelines.load_neo4j import load_entities_to_neo4j, load_resolution_matches_to_neo4j

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    entities_df = pd.read_csv(data_dir / "processed" / "clean_entities.csv", low_memory=False)
    load_entities_to_neo4j(entities_df)

    matches_path = data_dir / "processed" / "entity_resolution_matches.csv"
    if matches_path.exists():
        matches_df = pd.read_csv(matches_path)
        load_resolution_matches_to_neo4j(matches_df)

    return len(entities_df)


def task_load_qdrant(**ctx):
    import pandas as pd
    from pathlib import Path
    import os
    from pipelines.load_qdrant import load_embeddings_to_qdrant
    from pipelines.embeddings import load_embeddings

    data_dir = Path(os.environ.get("DATA_DIR", "/opt/airflow/data"))
    entities_df = pd.read_csv(data_dir / "processed" / "clean_entities.csv", low_memory=False)
    embeddings = load_embeddings()
    count = load_embeddings_to_qdrant(entities_df, embeddings)
    ctx["ti"].xcom_push(key="qdrant_indexed", value=count)
    return count


# ── Task Definitions ───────────────────────────────────────────────────────────

extract_gleif = PythonOperator(
    task_id="extract_gleif_records",
    python_callable=task_extract_gleif,
    dag=dag,
)

extract_opensanctions = PythonOperator(
    task_id="extract_opensanctions_records",
    python_callable=task_extract_opensanctions,
    dag=dag,
)

clean = PythonOperator(
    task_id="clean_and_normalize",
    python_callable=task_clean,
    dag=dag,
)

validate = PythonOperator(
    task_id="validate_data_quality",
    python_callable=task_validate,
    dag=dag,
)

embed = PythonOperator(
    task_id="generate_embeddings",
    python_callable=task_embed,
    dag=dag,
)

entity_resolution = PythonOperator(
    task_id="run_entity_resolution",
    python_callable=task_entity_resolution,
    dag=dag,
)

load_postgres = PythonOperator(
    task_id="load_postgres",
    python_callable=task_load_postgres,
    dag=dag,
)

load_neo4j = PythonOperator(
    task_id="load_neo4j",
    python_callable=task_load_neo4j,
    dag=dag,
)

load_qdrant = PythonOperator(
    task_id="load_qdrant",
    python_callable=task_load_qdrant,
    dag=dag,
)

# ── DAG Dependencies ───────────────────────────────────────────────────────────
#
#  extract_gleif ──┐
#                  ├──> clean ──> validate ──> embed ──> entity_resolution ──┐
# extract_opensanctions                                                        │
#                                                                              ├──> load_postgres
#                                                                              ├──> load_neo4j
#                                                                              └──> load_qdrant

[extract_gleif, extract_opensanctions] >> clean
clean >> validate >> embed >> entity_resolution
entity_resolution >> [load_postgres, load_neo4j, load_qdrant]
