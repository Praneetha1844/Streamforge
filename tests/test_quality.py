from datetime import timedelta
from pathlib import Path

import pytest
from conftest import FIXED_NOW, ROOT

from streamforge.quality import Rule, evaluate, load_rules


def rec(**fields: object) -> dict[str, object]:
    return {"type": "order.placed", "payload": {}, "processed_at": FIXED_NOW, **fields}


def run(rule: Rule, *records: dict[str, object]) -> tuple[int, int]:
    [result] = evaluate([rule], records, FIXED_NOW).results
    return result.checked, result.violations


def test_shipped_rules_file_is_valid() -> None:
    rules = load_rules(ROOT / "quality" / "rules.yaml")
    assert {r.type for r in rules} == {"not_null", "range", "unique", "freshness"}


def test_not_null_counts_missing_and_none() -> None:
    rule = Rule("r", "not_null", "payload.order_id")
    records = [
        rec(payload={"order_id": "a"}),
        rec(payload={"order_id": None}),
        rec(payload={}),
    ]
    assert run(rule, *records) == (3, 2)


def test_range_checks_bounds_and_rejects_non_numbers() -> None:
    rule = Rule("r", "range", "payload.n", params={"min": 0, "max": 10})
    records = [rec(payload={"n": v}) for v in (0, 10, -1, 11, "5", True, None)]
    assert run(rule, *records) == (7, 5)


def test_range_with_only_a_minimum() -> None:
    rule = Rule("r", "range", "payload.n", params={"min": 1})
    assert run(rule, rec(payload={"n": 10**9}), rec(payload={"n": 0})) == (2, 1)


def test_unique_counts_duplicates_and_ignores_missing() -> None:
    rule = Rule("r", "unique", "payload.id")
    records = [rec(payload={"id": "a"}), rec(payload={"id": "a"}), rec(payload={"id": "b"}), rec()]
    assert run(rule, *records) == (4, 1)


def test_freshness_uses_the_supplied_clock() -> None:
    rule = Rule("r", "freshness", "processed_at", params={"max_age_seconds": 60})
    records = [
        rec(processed_at=FIXED_NOW - timedelta(seconds=30)),
        rec(processed_at=FIXED_NOW - timedelta(seconds=61)),
        rec(processed_at="not-a-date"),
    ]
    assert run(rule, *records) == (3, 2)


def test_rule_is_scoped_to_its_event_type() -> None:
    rule = Rule("r", "not_null", "payload.x", event_type="payment.settled")
    records = [rec(type="order.placed"), rec(type="payment.settled")]
    assert run(rule, *records) == (1, 1)


def test_report_aggregates_results() -> None:
    good = Rule("good", "not_null", "type")
    bad = Rule("bad", "not_null", "payload.x")
    report = evaluate([good, bad], [rec()], FIXED_NOW)

    assert report.passed is False
    summary = report.to_dict()
    assert [(r["name"], r["passed"]) for r in summary["rules"]] == [("good", True), ("bad", False)]


@pytest.mark.parametrize(
    "body, message",
    [
        ("rules: 5", "top-level 'rules' list"),
        ("rules: [{name: a, type: nope, field: x}]", "type must be one of"),
        ("rules: [{type: not_null, field: x}]", "'name' and 'field' are required"),
        ("rules: [{name: a, type: range, field: x}]", "range needs"),
        ("rules: [{name: a, type: freshness, field: x}]", "max_age_seconds"),
    ],
)
def test_malformed_rules_are_rejected(tmp_path: Path, body: str, message: str) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(body)
    with pytest.raises(ValueError, match=message):
        load_rules(path)
