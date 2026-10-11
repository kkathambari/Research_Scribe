import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.base import Base
from app.db.session import engine
import app.models  # Ensures all models are registered
from app.api.v1 import (
    projects,
    repositories,
    journals,
    workflow,
    sources,
    evidence,
    manuscripts,
    verification,
    writing,
    export,
)

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ResearchScribe v3.0: An Evidence-Grounded GitHub-to-Research-Paper Generation and Journal Formatting System"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(repositories.router, prefix=settings.API_V1_STR)
app.include_router(journals.router, prefix=settings.API_V1_STR)
app.include_router(workflow.router, prefix=settings.API_V1_STR)
app.include_router(sources.router, prefix=settings.API_V1_STR)
app.include_router(evidence.router, prefix=settings.API_V1_STR)
app.include_router(manuscripts.router, prefix=settings.API_V1_STR)
app.include_router(verification.router, prefix=settings.API_V1_STR)
app.include_router(writing.router, prefix=settings.API_V1_STR)
app.include_router(export.router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ResearchScribe API",
        "version": settings.VERSION,
        "database": "sqlite",
        "llm_provider": settings.LLM_PROVIDER
    }

# Mount static frontend directory if available
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_frontend_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Welcome to ResearchScribe API. Access docs at /docs"}
else:
    @app.get("/")
    def root():
        return {
            "message": "Welcome to ResearchScribe API",
            "docs": "/docs",
            "version": settings.VERSION
        }
