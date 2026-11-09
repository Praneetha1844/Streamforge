"""A minimal forward-only SQL migration runner.

Migrations are ``NNN_description.sql`` files applied in name order. Applied versions are
recorded in ``schema_migrations``. Each migration runs in its own transaction.
shortcut: no down-migrations and no locking between concurrent runners, use a dedicated
migration tool (Alembic, Flyway) if the schema outgrows this.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from pathlib import Path

log = logging.getLogger(__name__)

_NAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")


def pending_migrations(directory: Path, applied: Iterable[str]) -> list[Path]:
    """Return the migration files in ``directory`` whose names are not in ``applied``."""
    done = set(applied)
    files = sorted(directory.glob("*.sql"))
    for path in files:
        if not _NAME.match(path.name):
            raise ValueError(f"migration file name must match NNN_description.sql: {path.name}")
    return [path for path in files if path.name not in done]


def apply_migrations(dsn: str, directory: Path) -> list[str]:
    """Apply pending migrations to the database and return the applied file names."""
    import psycopg  # imported here so the core works without the postgres extra

    applied_now: list[str] = []
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        conn.commit()
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        for path in pending_migrations(directory, (row[0] for row in rows)):
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))  # type: ignore[arg-type]
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            log.info("applied migration", extra={"migration": path.name})
            applied_now.append(path.name)
    return applied_now
