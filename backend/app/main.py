"""FastAPI entrypoint.

Run locally with:
    cd backend
    uvicorn app.main:app --reload

Once running, open http://127.0.0.1:8000/ in your browser — the static
frontend (Leaflet map) is served from the same process. The OpenAPI docs
are at http://127.0.0.1:8000/docs.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, engine
from .routers import ai, analytics, forecast, readings, sections


def _ensure_seed():
    """If the DB is empty on first run, populate sample data so the demo works."""
    from sqlalchemy.orm import Session

    from . import models
    from .seed import seed_sample_data

    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        if db.query(models.Section).count() == 0:
            seed_sample_data(db)


_ensure_seed()

app = FastAPI(
    title="Urban Grid GIS",
    version="1.0.0",
    description=(
        "Modern reimplementation of a 2006 university master's graduate project: a "
        "geographic information system for planning repair work on a city's "
        "electrical network. Faithful to the original feature set, with a "
        "natural-language query endpoint added for 2026."
    ),
)

# Open CORS for the demo. Tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sections.router)
app.include_router(readings.router)
app.include_router(analytics.router)
app.include_router(forecast.router)
app.include_router(ai.router)


@app.get("/api/health")
def health():
    return JSONResponse({"status": "ok"})


# --- Static frontend -----------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(FRONTEND_DIR / "index.html")
