from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "items.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Return a SQLAlchemy Engine for SQLite, ensuring data dir exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url or DB_URL, future=True)
    return engine


def table_exists(engine: Engine, table_name: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        ).fetchone()
        return result is not None


def get_row_count(engine: Engine, table_name: str) -> Optional[int]:
    if not table_exists(engine, table_name):
        return None
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return int(result.scalar_one())
