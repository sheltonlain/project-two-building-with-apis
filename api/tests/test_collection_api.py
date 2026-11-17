"""The /api/collection/ endpoint."""

import pytest
import responses
from django.core.cache import cache
from rest_framework.test import APIClient

from catalog import tcgdex
from catalog.tests.test_card_detail import detail
from collection.models import OwnedCard
from collection.tests.helpers import make_owned, make_user, make_variant, make_wish

URL = "/api/collection/"
CARD_URL = f"{tcgdex.BASE_URL}/cards/sv03.5-025"


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def api(ash):
    client = APIClient()
    client.raise_request_exception = False  # an unhandled error is a 500, as a real client sees
    client.force_authenticate(ash)
    return client


def test_create_fulfills_the_matching_wish_and_returns_the_full_entry(api, ash):
    make_variant("sv03.5-025", "Pikachu", "normal", "0.28")
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse", price="0.70", notes="binder page 3")

    response = api.post(
        URL,
        {"card_id": "sv03.5-025", "variant": "reverse", "quantity": 1, "notes": "first pull"},
        format="json",
    )

    assert response.status_code == 201
    owned = OwnedCard.objects.get(user=ash)
    body = response.json()
    assert body["id"] == owned.pk
    assert body["card"] == {
        "id": "sv03.5-025",
        "name": "Pikachu",
        "set_id": "sv03.5",
        "set_name": "151",
        "series": "",
        "rarity": "Common",
        "local_id": "025",
        "image": "https://assets.tcgdex.net/en/sv/sv03.5/025",
    }
    assert body["variant"] == "reverse"
    assert body["quantity"] == 1
    assert body["market_price"] == "0.70"
    assert body["price_updated"] == "2026-11-14T00:00:00Z"
    assert body["notes"] == "first pull"
    assert body["fulfilled_wish"]["id"] == wish.pk
    assert body["fulfilled_wish"]["variant"] == "reverse"
    assert body["fulfilled_wish"]["notes"] == "binder page 3"
    assert body["fulfilled_wish"]["fulfilled_at"] is not None
    wish.refresh_from_db()
    assert wish.fulfilled_by == owned


def test_patching_quantity_to_zero_deletes_the_entry(api, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal", "0.28", quantity=3)

    response = api.patch(f"{URL}{owned.pk}/", {"quantity": 0}, format="json")

    assert response.status_code == 204
    assert not OwnedCard.objects.filter(pk=owned.pk).exists()


@responses.activate
@pytest.mark.parametrize(
    ("tcgdex_reply", "variant", "status", "field", "message"),
    [
        ({"status": 500}, "normal", 503, "detail", "TCGdex is unavailable"),
        ({"status": 404}, "normal", 400, "card_id", "TCGdex has no card with this ID."),
        ({"json": detail()}, "holo", 400, "variant", "Pikachu doesn't come in that variant."),
    ],
    ids=["tcgdex-down", "unknown-card", "unsupported-variant"],
)
def test_create_reports_why_an_unstored_card_could_not_be_saved(
    api, tcgdex_reply, variant, status, field, message
):
    responses.get(CARD_URL, **tcgdex_reply)

    response = api.post(URL, {"card_id": "sv03.5-025", "variant": variant}, format="json")

    assert response.status_code == status
    error = response.json()[field]
    assert message in (error if isinstance(error, str) else error[0])
    assert not OwnedCard.objects.exists()


def test_patch_changes_quantity_and_notes(api, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal", "0.28")

    response = api.patch(f"{URL}{owned.pk}/", {"quantity": 4, "notes": "trade"}, format="json")

    assert response.status_code == 200
    assert (response.json()["quantity"], response.json()["notes"]) == (4, "trade")
    owned.refresh_from_db()
    assert (owned.quantity, owned.notes) == (4, "trade")


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"variant": "reverse"}, "variant"),
        ({"quantity": -1}, "quantity"),
        ({"notes": "x" * 501}, "notes"),
    ],
    ids=["variant", "negative-quantity", "long-notes"],
)
def test_patch_rejects_what_cannot_be_changed_or_is_invalid(api, ash, data, field):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal", "0.28", quantity=2)

    response = api.patch(f"{URL}{owned.pk}/", data, format="json")

    assert response.status_code == 400
    assert field in response.json()
    owned.refresh_from_db()
    assert (owned.quantity, owned.variant.variant, owned.notes) == (2, "normal", "")


@pytest.mark.parametrize(
    "data",
    [
        {"variant": "normal"},
        {"card_id": "sv03.5-025", "variant": "shiny"},
        {"card_id": "sv03.5-025", "variant": "normal", "quantity": 0},
    ],
    ids=["no-card", "unknown-variant", "zero-quantity"],
)
def test_create_rejects_invalid_input_without_asking_tcgdex(api, data):
    response = api.post(URL, data, format="json")  # responses isn't active: no request is made

    assert response.status_code == 400
    assert not OwnedCard.objects.exists()


@responses.activate
def test_create_fetches_and_stores_a_new_card_and_adds_the_quantity(api, ash):
    prices = {"normal": {"marketPrice": 0.28}}
    responses.get(CARD_URL, json=detail(tcgplayer=prices))

    response = api.post(
        URL, {"card_id": "sv03.5-025", "variant": "normal", "quantity": 3}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["quantity"], body["market_price"], body["fulfilled_wish"]) == (3, "0.28", None)


def test_create_works_for_a_stored_card_while_tcgdex_is_down(api, ash):
    make_variant("sv03.5-025", "Pikachu", "normal", "0.28")
    cache.set(tcgdex.OUTAGE_KEY, 1e12, 60)  # the circuit breaker is open

    response = api.post(URL, {"card_id": "sv03.5-025", "variant": "normal"}, format="json")

    assert response.status_code == 201


def test_delete_removes_the_entry(api, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")

    assert api.delete(f"{URL}{owned.pk}/").status_code == 204
    assert not OwnedCard.objects.exists()


def test_put_is_not_allowed(api, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")

    assert api.put(f"{URL}{owned.pk}/", {"quantity": 2}, format="json").status_code == 405


def test_list_is_paginated_and_shows_only_the_users_entries(api, ash):
    for number in range(30):
        make_owned(ash, f"sv03.5-{number:03}", f"Card {number}")
    make_owned(make_user("misty"), "sv03.5-999", "Staryu")

    first = api.get(URL).json()
    second = api.get(URL, {"page": 2}).json()

    assert first["count"] == 30
    assert len(first["results"]) == 24 and len(second["results"]) == 6
    names = [entry["card"]["name"] for entry in first["results"] + second["results"]]
    assert "Staryu" not in names
    assert first["results"][0]["card"]["name"] == "Card 29"  # newest first by default


def test_list_takes_the_websites_search_filters_and_ordering(api, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "normal", "0.28")
    make_owned(ash, "sv03.5-026", "Raichu", "reverse", "1.50")
    trade = make_owned(ash, "sv03.5-001", "Bulbasaur", "normal", None)
    trade.notes = "trade target"
    trade.save()

    def names(**query):
        return [entry["card"]["name"] for entry in api.get(URL, query).json()["results"]]

    assert names(search="trade") == ["Bulbasaur"]
    assert names(search="chu", ordering="name") == ["Pikachu", "Raichu"]
    assert names(variant="reverse") == ["Raichu"]
    assert names(rarity="Common", set="sv03.5", ordering="-price") == [
        "Raichu",
        "Pikachu",
        "Bulbasaur",  # no price last
    ]
    assert names(ordering="price") == ["Pikachu", "Raichu", "Bulbasaur"]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_users_entry_is_not_found(api, method):
    misty_entry = make_owned(make_user("misty"), "sv03.5-025", "Pikachu", quantity=2)

    response = getattr(api, method)(f"{URL}{misty_entry.pk}/", {"quantity": 0}, format="json")

    assert response.status_code == 404
    misty_entry.refresh_from_db()
    assert misty_entry.quantity == 2
