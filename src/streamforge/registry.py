"""File-based schema registry.

Schemas live in a directory as ``<event.type>.v<version>.json`` (JSON Schema, draft 2020-12).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from streamforge.domain import Event, SchemaViolation, UnknownSchema

_MAX_ERRORS_REPORTED = 5


class SchemaRegistry:
    """Validates event payloads against the schema for their (type, version)."""

    def __init__(self, schemas: Mapping[tuple[str, int], dict[str, Any]]) -> None:
        self._validators: dict[tuple[str, int], Draft202012Validator] = {}
        for key, schema in schemas.items():
            Draft202012Validator.check_schema(schema)
            self._validators[key] = Draft202012Validator(schema)

    @classmethod
    def from_dir(cls, directory: Path) -> SchemaRegistry:
        """Load every ``<type>.v<N>.json`` file in ``directory``."""
        schemas: dict[tuple[str, int], dict[str, Any]] = {}
        for path in sorted(directory.glob("*.json")):
            event_type, sep, version = path.stem.rpartition(".v")
            if not sep or not event_type or not version.isdigit():
                raise ValueError(f"schema file name must be <type>.v<N>.json: {path.name}")
            schemas[(event_type, int(version))] = json.loads(path.read_text(encoding="utf-8"))
        if not schemas:
            raise ValueError(f"no schemas found in {directory}")
        return cls(schemas)

    def versions(self, event_type: str) -> list[int]:
        """Return the registered versions of an event type, ascending."""
        return sorted(v for t, v in self._validators if t == event_type)

    def validate(self, event: Event) -> None:
        """Raise ``UnknownSchema`` or ``SchemaViolation`` if the event is not acceptable."""
        validator = self._validators.get((event.type, event.schema_version))
        if validator is None:
            raise UnknownSchema(f"no schema for {event.type} v{event.schema_version}")
        errors = sorted(validator.iter_errors(event.payload), key=lambda e: list(map(str, e.path)))
        if errors:
            shown = [
                f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
                for e in errors[:_MAX_ERRORS_REPORTED]
            ]
            raise SchemaViolation("; ".join(shown))
