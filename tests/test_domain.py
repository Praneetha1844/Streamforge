import pytest
from conftest import FIXED_NOW, make_event
from pydantic import ValidationError

from streamforge.domain import Event, Record


def test_valid_envelope_parses() -> None:
    event = Event.model_validate(make_event())
    assert event.type == "order.placed"
    assert event.occurred_at.tzinfo is not None


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Event.model_validate(make_event(occurred_at="2026-01-01T00:00:00"))


def test_unknown_envelope_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Event.model_validate(make_event(unexpected="x"))


@pytest.mark.parametrize("bad_type", ["Order.Placed", "order", "order..placed", ""])
def test_malformed_type_is_rejected(bad_type: str) -> None:
    with pytest.raises(ValidationError):
        Event.model_validate(make_event(type=bad_type))


def test_schema_version_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Event.model_validate(make_event(schema_version=0))


def test_record_as_dict_exposes_all_fields() -> None:
    record = Record("e1", "t.x", "s", 1, FIXED_NOW, FIXED_NOW, {"a": 1})
    assert record.as_dict() == {
        "event_id": "e1",
        "type": "t.x",
        "source": "s",
        "schema_version": 1,
        "occurred_at": FIXED_NOW,
        "processed_at": FIXED_NOW,
        "payload": {"a": 1},
    }
