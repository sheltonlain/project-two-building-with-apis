from datetime import UTC, datetime
from decimal import Decimal

import pytest

from collection import services
from collection.tests.helpers import make_owned, make_user


@pytest.mark.django_db
def test_value_totals_priced_entries_and_counts_the_unpriced_ones():
    ash, misty = make_user("ash"), make_user("misty")
    make_owned(
        ash,
        "sv03.5-025",
        "Pikachu",
        "normal",
        price="0.28",
        quantity=3,
        updated=datetime(2026, 11, 14, tzinfo=UTC),
    )
    make_owned(
        ash,
        "sv03.5-025",
        "Pikachu",
        "reverse",
        price="0.70",
        updated=datetime(2026, 11, 10, tzinfo=UTC),
    )
    make_owned(ash, "sv03.5-006", "Charizard", "holo", price=None, quantity=2)
    make_owned(ash, "sv03.5-001", "Bulbasaur", "normal", price=None)
    make_owned(misty, "sv03.5-120", "Starmie", "normal", price="99.00")  # not ash's

    value = services.collection_value(ash)

    assert value["total"] == Decimal("1.54")  # 3 × 0.28 + 1 × 0.70
    assert value["unpriced"] == 2
    assert value["as_of"] == datetime(2026, 11, 10, tzinfo=UTC)  # oldest stored price


@pytest.mark.django_db
def test_an_empty_collection_is_worth_zero():
    value = services.collection_value(make_user("ash"))

    assert value == {"total": Decimal("0"), "unpriced": 0, "as_of": None}


@pytest.mark.django_db
def test_the_total_is_rounded_to_cents():
    ash = make_user("ash")
    make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.10", quantity=3)

    assert str(services.collection_value(ash)["total"]) == "0.30"
