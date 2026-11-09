"""Data-quality rules defined in YAML and evaluated against stored records.

Rule types: ``not_null``, ``range`` (min and/or max), ``unique`` and ``freshness``
(``max_age_seconds`` relative to ``now``). A rule may be limited to one ``event_type``.
Fields use dotted paths into a record, for example ``payload.total_cents``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

RULE_TYPES = {"not_null", "range", "unique", "freshness"}
_MISSING = object()


@dataclass(frozen=True, slots=True)
class Rule:
    """One data-quality rule."""

    name: str
    type: str
    field: str
    event_type: str | None = None
    params: Mapping[str, Any] = dataclass_field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Outcome of one rule: how many records it checked and how many violated it."""

    name: str
    type: str
    checked: int
    violations: int

    @property
    def passed(self) -> bool:
        """True when no record violated the rule."""
        return self.violations == 0


@dataclass(frozen=True, slots=True)
class QualityReport:
    """All rule results for one evaluation."""

    results: list[RuleResult]

    @property
    def passed(self) -> bool:
        """True when every rule passed."""
        return all(result.passed for result in self.results)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly summary."""
        return {
            "passed": self.passed,
            "rules": [
                {
                    "name": r.name,
                    "type": r.type,
                    "checked": r.checked,
                    "violations": r.violations,
                    "passed": r.passed,
                }
                for r in self.results
            ],
        }


def load_rules(path: Path) -> list[Rule]:
    """Parse a rules YAML file. Raise ``ValueError`` for malformed rules."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("rules"), list):
        raise ValueError("rules file must contain a top-level 'rules' list")
    rules: list[Rule] = []
    for index, raw in enumerate(document["rules"]):
        if not isinstance(raw, dict):
            raise ValueError(f"rule #{index} must be a mapping")
        rule_type = raw.get("type")
        if rule_type not in RULE_TYPES:
            raise ValueError(f"rule #{index}: type must be one of {sorted(RULE_TYPES)}")
        if not raw.get("name") or not raw.get("field"):
            raise ValueError(f"rule #{index}: 'name' and 'field' are required")
        params = {k: v for k, v in raw.items() if k not in {"name", "type", "field", "event_type"}}
        _check_params(index, rule_type, params)
        rules.append(Rule(raw["name"], rule_type, raw["field"], raw.get("event_type"), params))
    return rules


def _check_params(index: int, rule_type: str, params: Mapping[str, Any]) -> None:
    if rule_type == "range" and not ({"min", "max"} & params.keys()):
        raise ValueError(f"rule #{index}: range needs 'min' and/or 'max'")
    if rule_type == "freshness" and "max_age_seconds" not in params:
        raise ValueError(f"rule #{index}: freshness needs 'max_age_seconds'")


def _get(record: Mapping[str, Any], dotted: str) -> Any:
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def evaluate(
    rules: Iterable[Rule], records: Iterable[Mapping[str, Any]], now: datetime
) -> QualityReport:
    """Evaluate every rule against the records. ``now`` is explicit to keep this pure."""
    all_records = list(records)
    results = []
    for rule in rules:
        scope = [r for r in all_records if rule.event_type in (None, r.get("type"))]
        values = [_get(r, rule.field) for r in scope]
        results.append(RuleResult(rule.name, rule.type, len(scope), _violations(rule, values, now)))
    return QualityReport(results)


def _violations(rule: Rule, values: list[Any], now: datetime) -> int:
    if rule.type == "not_null":
        return sum(1 for v in values if v is _MISSING or v is None)
    if rule.type == "unique":
        present = [v for v in values if v is not _MISSING and v is not None]
        return len(present) - len(set(present))
    if rule.type == "range":
        low, high = rule.params.get("min"), rule.params.get("max")
        return sum(1 for v in values if not _in_range(v, low, high))
    max_age = float(rule.params["max_age_seconds"])
    return sum(1 for v in values if not _is_fresh(v, now, max_age))


def _in_range(value: Any, low: float | None, high: float | None) -> bool:
    if not _is_number(value):
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _is_fresh(value: Any, now: datetime, max_age: float) -> bool:
    if not isinstance(value, datetime):
        return False
    return (now - value).total_seconds() <= max_age
