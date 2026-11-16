from decimal import Decimal

import pytest
import responses
from django.contrib.auth import get_user_model

from catalog import tcgdex
from catalog.models import Card, CardVariant
from catalog.tests.test_card_detail import detail
from collection import services
from collection.models import OwnedCard

CARDS_URL = f"{tcgdex.BASE_URL}/cards"
PRICES = {
    "updated": "2026-11-14T20:07:54.000Z",
    "unit": "USD",
    "normal": {"marketPrice": 0.28},
    "reverse-holofoil": {"marketPrice": 0.7},
}


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="ash", email="ash@example.com", password="x"
    )


@responses.activate
def test_first_add_stores_the_card_and_a_second_add_increments_the_quantity(user):
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(variants={"normal": True, "reverse": True}, tcgplayer=PRICES),
    )

    services.add_copy(user, "sv03.5-025", "reverse")
    owned = services.add_copy(user, "sv03.5-025", "reverse")

    card = Card.objects.filter(tcgdex_id="sv03.5-025").first()
    assert card is not None
    assert (card.name, card.set_name, card.rarity, card.local_id) == (
        "Pikachu",
        "151",
        "Common",
        "025",
    )
    prices = {v.variant: v.market_price for v in card.variants.all()}
    assert prices == {"normal": Decimal("0.28"), "reverse": Decimal("0.70")}
    assert all(v.price_updated is not None for v in card.variants.all())
    assert OwnedCard.objects.get() == owned
    assert (owned.user, owned.variant.variant, owned.quantity) == (user, "reverse", 2)
    assert len(responses.calls) == 1  # the second add used the stored card
    assert CardVariant.objects.count() == 2


@responses.activate
def test_adding_a_variant_the_card_does_not_have_is_rejected(user):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail(variants={"normal": True}))

    with pytest.raises(services.UnsupportedVariant):
        services.add_copy(user, "sv03.5-025", "holo")

    assert not OwnedCard.objects.exists()
    assert [v.variant for v in CardVariant.objects.all()] == ["normal"]


@responses.activate
def test_removing_copies_decrements_and_the_last_one_deletes_the_entry_but_keeps_the_card(user):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail())
    services.add_copy(user, "sv03.5-025", "normal")
    owned = services.add_copy(user, "sv03.5-025", "normal")

    services.remove_copy(owned)
    assert OwnedCard.objects.get().quantity == 1

    remaining = services.remove_copy(OwnedCard.objects.get())
    assert remaining is None
    assert not OwnedCard.objects.exists()
    assert Card.objects.filter(tcgdex_id="sv03.5-025").exists()
    assert CardVariant.objects.filter(card__tcgdex_id="sv03.5-025").exists()


@responses.activate
def test_a_stored_card_gets_its_series_from_the_cached_set_list(user):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail())
    groups = [{"name": "Scarlet & Violet", "sets": [{"id": "sv03.5", "name": "151"}]}]
    tcgdex.cache.set(tcgdex.SET_GROUPS_KEY, groups, tcgdex.OPTIONS_CACHE_SECONDS)

    services.add_copy(user, "sv03.5-025", "normal")

    assert Card.objects.get().series == "Scarlet & Violet"
    assert len(responses.calls) == 1  # no extra request for the series
