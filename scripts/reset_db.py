"""Wipe the SQLite DB and re-seed from sample data.

Usage (from the repo root):
    python scripts/reset_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `app` importable when running this script from the repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy.orm import Session  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.seed import seed_sample_data  # noqa: E402


def main() -> None:
    print("Dropping all tables…")
    Base.metadata.drop_all(bind=engine)
    print("Creating tables…")
    Base.metadata.create_all(bind=engine)
    print("Seeding sample data…")
    with Session(engine) as db:
        seed_sample_data(db)
    print("Done.")


if __name__ == "__main__":
    main()
