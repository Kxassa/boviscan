from __future__ import annotations

import sqlite3
from pathlib import Path

from ..settings import settings

MIGRATIONS = Path(__file__).resolve().parents[3] / "migrations" / "001_init.sql"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    c = conn or get_connection()
    sql = MIGRATIONS.read_text(encoding="utf-8")
    c.executescript(sql)
    # Lightweight additive migration for DBs created before status column
    cols = {r[1] for r in c.execute("PRAGMA table_info(weighing_sessions)").fetchall()}
    if "status" not in cols:
        c.execute(
            "ALTER TABLE weighing_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
        )
    c.commit()
    if own:
        c.close()
