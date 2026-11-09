import pytest
from conftest import Harness

from streamforge.generator import generate_events


def test_same_seed_produces_identical_events() -> None:
    assert list(generate_events(25, seed=7)) == list(generate_events(25, seed=7))


def test_different_seeds_produce_different_events() -> None:
    assert list(generate_events(25, seed=1)) != list(generate_events(25, seed=2))


def test_count_and_unique_ids() -> None:
    events = list(generate_events(50, seed=3))
    assert len(events) == 50
    assert len({e["id"] for e in events}) == 50


def test_every_valid_event_passes_the_pipeline(harness: Harness) -> None:
    for event in generate_events(200, seed=11):
        harness.publish(event)

    result = harness.processor.process_batch(1000)

    assert (result.processed, result.dead_lettered) == (200, 0)


def test_every_corrupted_event_is_rejected(harness: Harness) -> None:
    for event in generate_events(100, seed=5, invalid_ratio=1.0):
        harness.publish(event)

    result = harness.processor.process_batch(1000)

    assert (result.processed, result.dead_lettered) == (0, 100)


@pytest.mark.parametrize("kwargs", [{"count": -1}, {"count": 1, "invalid_ratio": 1.5}])
def test_invalid_arguments_are_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        list(generate_events(seed=1, **kwargs))  # type: ignore[arg-type]
