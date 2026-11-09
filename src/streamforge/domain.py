"""Core domain types: the event envelope, stored records, dead letters and errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RejectReason(StrEnum):
    """Why a message was routed to the dead-letter store."""

    INVALID_ENVELOPE = "INVALID_ENVELOPE"
    UNKNOWN_SCHEMA = "UNKNOWN_SCHEMA"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    TRANSFORM_ERROR = "TRANSFORM_ERROR"
    SINK_FAILURE = "SINK_FAILURE"


class StreamforgeError(Exception):
    """Base class for all expected errors."""


class UnknownSchema(StreamforgeError):
    """No schema is registered for the event type and version."""


class SchemaViolation(StreamforgeError):
    """The payload does not satisfy the registered schema."""


class StoreError(StreamforgeError):
    """A store operation failed. Treated as transient and retried."""


class QueueError(StreamforgeError):
    """A queue operation failed."""


class Event(BaseModel):
    """The envelope every message must carry. The payload is validated separately."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    type: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    source: str = Field(min_length=1, max_length=128)
    schema_version: int = Field(ge=1)
    occurred_at: datetime
    payload: dict[str, Any]

    @field_validator("occurred_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


@dataclass(frozen=True, slots=True)
class Record:
    """A validated, transformed event as it is stored."""

    event_id: str
    type: str
    source: str
    schema_version: int
    occurred_at: datetime
    processed_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a plain mapping, used by the API and the quality checks."""
        return {
            "event_id": self.event_id,
            "type": self.type,
            "source": self.source,
            "schema_version": self.schema_version,
            "occurred_at": self.occurred_at,
            "processed_at": self.processed_at,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class DeadLetter:
    """A raw message that could not be processed, with the reason."""

    raw: bytes
    reason: RejectReason
    detail: str
    failed_at: datetime
    id: int | None = None
