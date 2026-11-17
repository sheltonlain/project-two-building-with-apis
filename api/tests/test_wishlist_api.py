"""The /api/wishlist/ endpoint."""

import pytest
import responses
from django.utils import timezone
from rest_framework.test import APIClient

from catalog import tcgdex
from catalog.tests.test_card_detail import detail
from collection.models import Wish
from collection.tests.helpers import make_owned, make_user, make_variant, make_wish

URL = "/api/wishlist/"
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


def test_create_wishes_for_a_variant_even_when_it_is_owned(api, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "reverse", "0.70")

    response = api.post(
        URL,
        {"card_id": "sv03.5-025", "variant": "reverse", "notes": "a second one"},
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    wish = Wish.objects.get(user=ash)
    assert (body["id"], body["variant"], body["notes"]) == (wish.pk, "reverse", "a second one")
    assert body["card"]["id"] == "sv03.5-025"
    assert body["market_price"] == "0.70"
    assert body["fulfilled_at"] is None


def test_creating_the_same_wish_again_returns_the_existing_one(api, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "normal")

    response = api.post(URL, {"card_id": "sv03.5-025", "variant": "normal"}, format="json")

    assert response.status_code == 200
    assert response.json()["id"] == wish.pk
    assert Wish.objects.count() == 1


@responses.activate
@pytest.mark.parametrize(
    ("tcgdex_reply", "variant", "status", "field"),
    [
        ({"status": 500}, "normal", 503, "detail"),
        ({"status": 404}, "normal", 400, "card_id"),
        ({"json": detail()}, "holo", 400, "variant"),
        ({"json": detail()}, "any", 400, "variant"),
    ],
    ids=["tcgdex-down", "unknown-card", "unsupported-variant", "no-such-variant"],
)
def test_create_requires_a_real_card_and_variant(api, tcgdex_reply, variant, status, field):
    responses.get(CARD_URL, **tcgdex_reply)

    response = api.post(URL, {"card_id": "sv03.5-025", "variant": variant}, format="json")

    assert response.status_code == status
    assert field in response.json()
    assert not Wish.objects.exists()


def test_patch_changes_notes_only(api, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "normal", notes="old")

    ok = api.patch(f"{URL}{wish.pk}/", {"notes": "new"}, format="json")
    variant = api.patch(f"{URL}{wish.pk}/", {"variant": "reverse"}, format="json")
    too_long = api.patch(f"{URL}{wish.pk}/", {"notes": "x" * 501}, format="json")

    assert ok.status_code == 200 and ok.json()["notes"] == "new"
    assert variant.status_code == 400 and "variant" in variant.json()
    assert too_long.status_code == 400 and "notes" in too_long.json()
    wish.refresh_from_db()
    assert (wish.notes, wish.variant.variant) == ("new", "normal")


def test_delete_removes_the_wish(api, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu")

    assert api.delete(f"{URL}{wish.pk}/").status_code == 204
    assert not Wish.objects.exists()


def test_list_includes_fulfilled_wishes_and_takes_the_filters(api, ash):
    make_wish(ash, "sv03.5-025", "Pikachu", "normal", price="0.28")
    make_wish(ash, "sv03.5-026", "Raichu", "reverse", price="1.50", fulfilled_at=timezone.now())
    make_wish(make_user("misty"), "sv03.5-001", "Bulbasaur")

    def names(**query):
        return [wish["card"]["name"] for wish in api.get(URL, query).json()["results"]]

    assert names(ordering="name") == ["Pikachu", "Raichu"]
    assert names(ordering="-price") == ["Raichu", "Pikachu"]
    assert names(variant="reverse") == ["Raichu"]
    assert names(search="pika") == ["Pikachu"]
    assert api.get(URL, {"variant": "reverse"}).json()["results"][0]["fulfilled_at"]


def test_list_is_paginated(api, ash):
    for number in range(25):
        make_wish(ash, f"sv03.5-{number:03}", f"Card {number}")

    body = api.get(URL, {"page": 2}).json()

    assert body["count"] == 25
    assert len(body["results"]) == 1


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_users_wish_is_not_found(api, method):
    misty_wish = make_wish(make_user("misty"), "sv03.5-025", "Pikachu", notes="mine")

    response = getattr(api, method)(f"{URL}{misty_wish.pk}/", {"notes": "hacked"}, format="json")

    assert response.status_code == 404
    misty_wish.refresh_from_db()
    assert misty_wish.notes == "mine"


def test_a_collection_entry_created_through_the_api_fulfills_only_the_same_variant(api, ash):
    make_variant("sv03.5-025", "Pikachu", "normal")
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse")

    response = api.post(
        "/api/collection/", {"card_id": "sv03.5-025", "variant": "normal"}, format="json"
    )

    assert response.json()["fulfilled_wish"] is None
    wish.refresh_from_db()
    assert wish.fulfilled_at is None
