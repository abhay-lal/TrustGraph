from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import entities, resolution, semantic, llm, pipeline
from app.db.database import create_tables

app = FastAPI(
    title="TrustGraph API",
    description="LLM-assisted entity resolution and semantic search for legal entities",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    try:
        create_tables()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("DB init skipped: %s", e)


app.include_router(entities.router, prefix="/entities", tags=["entities"])
app.include_router(resolution.router, prefix="/entity-resolution", tags=["resolution"])
app.include_router(semantic.router, prefix="/semantic-search", tags=["search"])
app.include_router(llm.router, prefix="/llm", tags=["llm"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "trustgraph-api"}
