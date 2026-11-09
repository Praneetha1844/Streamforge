from streamforge.transform import (
    compose,
    default_transforms,
    derive_order_totals,
    identity,
    normalise_currency,
)

ORDER = {
    "currency": "usd",
    "items": [
        {"sku": "A", "qty": 2, "unit_price_cents": 500},
        {"sku": "B", "qty": 1, "unit_price_cents": 250},
    ],
}


def test_normalise_currency_uppercases() -> None:
    assert normalise_currency({"currency": "eur"})["currency"] == "EUR"


def test_derive_order_totals() -> None:
    result = derive_order_totals(ORDER)
    assert result["item_count"] == 3
    assert result["total_cents"] == 1250


def test_transforms_do_not_mutate_their_input() -> None:
    before = {"currency": "usd", "items": [dict(i) for i in ORDER["items"]]}
    derive_order_totals(before)
    normalise_currency(before)
    assert before["currency"] == "usd"
    assert "total_cents" not in before


def test_compose_applies_steps_in_order() -> None:
    result = compose(normalise_currency, derive_order_totals)(ORDER)
    assert result["currency"] == "USD"
    assert result["total_cents"] == 1250


def test_compose_of_nothing_is_identity() -> None:
    assert compose()({"a": 1}) == {"a": 1}


def test_default_transforms_cover_known_types_only() -> None:
    transforms = default_transforms()
    assert set(transforms) == {"order.placed", "payment.settled"}
    assert identity({"x": 1}) == {"x": 1}
