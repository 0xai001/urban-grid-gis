"""Database setup — SQLite via SQLAlchemy.

For a 2026 portfolio project, SQLite is a great choice:
- Zero install (file-based)
- Ships with Python
- Plenty fast for the demo's data volume
- Trivial to swap for PostgreSQL/PostGIS later (one URL change)
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# DB file lives at the repo root by default.
DB_PATH = Path(os.getenv("URBAN_GRID_DB", Path(__file__).resolve().parents[2] / "urban_grid.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite + threaded server
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a per-request DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
