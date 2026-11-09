import json
from pathlib import Path

import pytest
from conftest import ROOT

from streamforge.cli import main


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run from an empty directory so no local .env is read, and point at the shipped files."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SF_SCHEMA_DIR", str(ROOT / "schemas"))
    monkeypatch.setenv("SF_RULES_PATH", str(ROOT / "quality" / "rules.yaml"))


def test_generate_writes_json_lines_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["generate", "--count", "3", "--seed", "2"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    assert all(json.loads(line)["id"].startswith("evt-2-") for line in lines)


def test_generate_writes_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    assert main(["generate", "--count", "5", "--out", str(target)]) == 0
    assert len(target.read_text().splitlines()) == 5


def test_demo_run_drains_the_queue_and_exits() -> None:
    assert main(["run", "--demo", "30", "--seed", "3", "--no-metrics-server"]) == 0


def test_quality_on_an_empty_store_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quality"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True


def test_invalid_configuration_returns_exit_code_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SF_STORE_BACKEND", "postgres")
    assert main(["quality"]) == 2
    assert "SF_DATABASE_URL" in capsys.readouterr().err


def test_migrate_without_database_url_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["migrate"]) == 2
    assert "SF_DATABASE_URL" in capsys.readouterr().err
