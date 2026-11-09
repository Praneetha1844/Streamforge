from pathlib import Path

import pytest
from conftest import make_event

from streamforge.domain import Event, SchemaViolation, UnknownSchema
from streamforge.registry import SchemaRegistry


def test_loads_all_versions_from_directory(registry: SchemaRegistry) -> None:
    assert registry.versions("order.placed") == [1, 2]
    assert registry.versions("payment.settled") == [1]
    assert registry.versions("nothing.here") == []


def test_valid_payload_passes(registry: SchemaRegistry) -> None:
    registry.validate(Event.model_validate(make_event()))


def test_unknown_version_is_rejected(registry: SchemaRegistry) -> None:
    with pytest.raises(UnknownSchema, match="order.placed v9"):
        registry.validate(Event.model_validate(make_event(schema_version=9)))


def test_violation_reports_the_failing_path(registry: SchemaRegistry) -> None:
    event = make_event()
    event["payload"]["items"][0]["qty"] = 0
    with pytest.raises(SchemaViolation, match="items/0/qty"):
        registry.validate(Event.model_validate(event))


def test_missing_required_field_is_reported(registry: SchemaRegistry) -> None:
    event = make_event()
    del event["payload"]["customer_id"]
    with pytest.raises(SchemaViolation, match="customer_id"):
        registry.validate(Event.model_validate(event))


def test_v1_rejects_channel_but_v2_accepts_it(registry: SchemaRegistry) -> None:
    v1 = make_event()
    v1["payload"]["channel"] = "web"
    with pytest.raises(SchemaViolation):
        registry.validate(Event.model_validate(v1))

    v2 = make_event(schema_version=2)
    v2["payload"]["channel"] = "web"
    registry.validate(Event.model_validate(v2))


def test_rejects_malformed_schema_file_name(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{}")
    with pytest.raises(ValueError, match="<type>.v<N>.json"):
        SchemaRegistry.from_dir(tmp_path)


def test_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no schemas"):
        SchemaRegistry.from_dir(tmp_path)
