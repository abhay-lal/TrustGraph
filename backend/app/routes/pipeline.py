import json
from pathlib import Path
from fastapi import APIRouter
from app.services.postgres_service import get_latest_quality_run, get_pipeline_stats
from app.services.qdrant_service import get_collection_stats

router = APIRouter()

REPORTS_DIR = Path("/opt/airflow/data/reports")


@router.get("/stats")
def pipeline_stats():
    stats = get_pipeline_stats()
    qdrant = get_collection_stats()
    stats["vector_index_size"] = qdrant.get("vector_count", 0)
    return stats


@router.get("/latest-run")
def latest_run():
    run = get_latest_quality_run()
    return run or {"message": "No pipeline runs recorded yet"}


@router.get("/data-quality/latest")
def latest_quality():
    report_path = REPORTS_DIR / "data_quality_report.json"
    if report_path.exists():
        with open(report_path) as f:
            return json.load(f)
    run = get_latest_quality_run()
    return run or {"message": "No quality report available"}
