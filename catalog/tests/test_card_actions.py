"""The card detail page's owned and wished status, and its Add, "+", "−" and wishlist actions."""

import re
from html import unescape

import pytest
import responses
from django.urls import reverse
from django.utils import timezone

from catalog import tcgdex
from catalog.tests.test_card_detail import detail
from collection.models import OwnedCard, Wish
from collection.tests.helpers import make_owned, make_user, make_wish

CARD_URL = f"{tcgdex.BASE_URL}/cards/sv03.5-025"
PRICES = {"unit": "USD", "normal": {"marketPrice": 0.28}, "reverse-holofoil": {"marketPrice": 0.7}}
PIKACHU = detail(variants={"normal": True, "reverse": True}, tcgplayer=PRICES)


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def act(client, action, variant="normal", **headers):
    url = reverse(f"catalog:card_{action}", args=["sv03.5-025"])
    return client.post(url, {"variant": variant}, HTTP_HX_REQUEST="true", **headers)


def test_minus_on_the_copy_that_fulfilled_a_wish_brings_the_wish_back(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "reverse", "0.70")
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse", fulfilled_at=timezone.now())
    wish.fulfilled_by = owned
    wish.save()

    response = act(ash_client, "remove", "reverse")

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html and 'id="card-variants"' in html  # just the variants section
    assert not OwnedCard.objects.filter(user=ash).exists()  # the last copy, so the entry is gone
    assert Wish.objects.get(pk=wish.pk).fulfilled_at is None  # the wish is active again
    assert "Removed your last Reverse holo copy. Its wish is back on your wishlist." in html
    assert "On your wishlist" in html  # the redrawn section shows it
    assert 'id="nav-wish-count"' in html and 'hx-swap-oob="true"' in html  # nav count: 1
    assert ">1</span>" in html


@responses.activate
def test_each_variant_shows_only_the_signed_in_users_wishlist_status(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    make_wish(make_user("misty"), "sv03.5-025", "Pikachu", "normal")

    response = ash_client.get(reverse("catalog:card_detail", args=["sv03.5-025"]))

    variants = {v["code"]: v for v in response.context["variants"]}
    assert variants["reverse"]["wished"] is True
    assert variants["normal"]["wished"] is False  # misty's wish isn't ash's
    html = response.content.decode()
    assert html.count("On your wishlist") == 1
    assert 'aria-label="Add Normal to wishlist"' in html
    assert 'aria-label="Add Reverse holo to wishlist"' not in html


@responses.activate
def test_collection_and_wishlist_links_appear_only_with_matching_entries(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    page = reverse("catalog:card_detail", args=["sv03.5-025"])
    make_owned(make_user("misty"), "sv03.5-025", "Pikachu", "normal")  # not ash's

    neither = ash_client.get(page).content.decode()
    make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    owned = ash_client.get(page).content.decode()
    make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    both = ash_client.get(page).content.decode()

    query = "?q=Pikachu&amp;set=sv03.5"  # the pages' search and set filters, narrowed to this card
    collection = f'href="{reverse("collection:index")}{query}"'
    wishlist = f'href="{reverse("collection:wishlist")}{query}"'
    assert "View in my collection" not in neither and "View on my wishlist" not in neither
    assert collection in owned and "View in my collection" in owned
    assert "View on my wishlist" not in owned
    assert collection in both and wishlist in both and "View on my wishlist" in both


@responses.activate
def test_add_then_plus_steps_the_variant_and_says_so(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)

    added = act(ash_client, "add", "reverse").content.decode()
    plus = act(ash_client, "add", "reverse").content.decode()

    assert 'id="card-variants"' in added and "<html" not in added
    assert "Added 1 Reverse holo." in added and "1 owned" in added
    assert 'aria-label="Remove one Reverse holo"' in added  # the stepper replaced Add
    assert 'aria-label="Add Normal to collection"' in added  # the other variant is untouched
    assert "2 owned" in plus
    assert OwnedCard.objects.get(user=ash, variant__variant="reverse").quantity == 2
    assert 'id="nav-wish-count"' not in added  # no wish changed, so the nav isn't swapped


@responses.activate
def test_adding_a_wished_variant_fulfills_the_wish_and_updates_the_nav(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "normal")

    html = act(ash_client, "add", "normal").content.decode()

    assert Wish.objects.get(pk=wish.pk).fulfilled_at is not None
    assert "On your wishlist" not in html
    assert 'id="nav-wish-count"' in html and 'hx-swap-oob="true"' in html


def test_minus_with_copies_left_steps_down(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "normal", "0.28", quantity=2)

    html = act(ash_client, "remove", "normal").content.decode()

    assert "Removed 1 Normal." in html and "1 owned" in html
    assert OwnedCard.objects.get(user=ash).quantity == 1


def test_minus_never_touches_another_users_copies(ash_client):
    misty = make_owned(make_user("misty"), "sv03.5-025", "Pikachu", "normal", quantity=2)

    response = act(ash_client, "remove", "normal")

    assert response.status_code == 200
    assert OwnedCard.objects.get(pk=misty.pk).quantity == 2
    assert "Not in your collection" in response.content.decode()


@responses.activate
def test_add_to_wishlist_marks_the_variant_and_updates_the_nav(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)

    html = act(ash_client, "wish", "reverse").content.decode()
    again = act(ash_client, "wish", "reverse").content.decode()

    assert "Added Reverse holo to your wishlist." in html
    assert "On your wishlist" in html
    assert 'id="nav-wish-count"' in html and ">1</span>" in html
    assert "Reverse holo is already on your wishlist." in again
    assert Wish.objects.filter(user=ash).count() == 1


@responses.activate
def test_an_unsupported_variant_shows_the_error_above_the_variants(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)

    html = act(ash_client, "add", "first_edition").content.decode()

    assert "This card doesn't come in that variant." in unescape(html)
    assert 'id="card-variants"' in html and "Normal" in html  # the rows are still there
    assert not OwnedCard.objects.exists()


@responses.activate
def test_adding_during_an_outage_says_so_and_retry_probes(ash_client, ash):
    responses.get(CARD_URL, status=503)

    html = act(ash_client, "add", "normal").content.decode()

    assert "TCGdex, the card database, didn't respond" in unescape(html)
    retry = re.search(r"<button[^>]*>Retry</button>", html, re.S).group(0)
    assert f'hx-post="{reverse("catalog:card_add", args=["sv03.5-025"])}"' in retry
    assert """hx-vals='{"variant": "normal"}'""" in retry
    assert """hx-headers='{"X-User-Retry": "1"}'""" in retry

    responses.replace(responses.GET, CARD_URL, json=PIKACHU)
    retried = act(ash_client, "add", "normal", HTTP_X_USER_RETRY="1").content.decode()

    assert "Added 1 Normal." in retried  # reached TCGdex though the breaker is open
    assert OwnedCard.objects.get(user=ash).quantity == 1


def test_the_actions_require_sign_in(client, db):
    for action in ("add", "remove", "wish"):
        url = reverse(f"catalog:card_{action}", args=["sv03.5-025"])
        response = client.post(url, {"variant": "normal"})
        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))
