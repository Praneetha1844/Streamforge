from pathlib import Path

import pytest
from conftest import ROOT

from streamforge.migrate import pending_migrations


def test_shipped_migrations_are_ordered_and_well_named() -> None:
    names = [p.name for p in pending_migrations(ROOT / "migrations", [])]
    assert names == ["001_create_events.sql", "002_create_dead_letters.sql"]


def test_applied_migrations_are_skipped(tmp_path: Path) -> None:
    for name in ("001_a.sql", "002_b.sql", "003_c.sql"):
        (tmp_path / name).write_text("SELECT 1;")

    pending = pending_migrations(tmp_path, ["001_a.sql", "002_b.sql"])

    assert [p.name for p in pending] == ["003_c.sql"]


def test_badly_named_migration_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "create_table.sql").write_text("SELECT 1;")
    with pytest.raises(ValueError, match="NNN_description.sql"):
        pending_migrations(tmp_path, [])
