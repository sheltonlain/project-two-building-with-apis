import re
from datetime import timedelta
from decimal import Decimal

import pytest
import responses
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from catalog import tcgdex
from catalog.models import Card, CardVariant
from catalog.tests.test_card_detail import detail
from collection.models import Wish
from collection.tests.helpers import make_user, make_wish

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


def nav_wish_count(html):
    """The active-wish count in the nav (or in an out-of-band nav update), or None if absent."""
    match = re.search(r'id="nav-wish-count"[^>]*>\s*(\d+)\s*<', html)
    return int(match.group(1)) if match else None


def wish(client, variant):
    return client.post(reverse("catalog:tile_wish", args=["sv03.5-025"]), {"variant": variant})


@responses.activate
def test_wishing_from_a_tile_for_two_variants_shows_both_on_the_badge(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    ash_client.post(reverse("catalog:tile_add", args=["sv03.5-025"]), {"variant": "normal"})
    before = ash_client.get(reverse("catalog:tile_details", args=["sv03.5-025"])).content.decode()

    wish(ash_client, "reverse")
    html = wish(ash_client, "normal").content.decode()  # owning a variant doesn't stop a wish

    wishes = Wish.objects.filter(user=ash)
    assert sorted(w.variant.variant for w in wishes) == ["normal", "reverse"]
    assert all(w.variant.card.tcgdex_id == "sv03.5-025" for w in wishes)
    assert "On your wishlist: Normal, Reverse holo" in html
    assert "Add to wishlist" in before
    assert "Add to wishlist" not in html  # the selected variant is wished for now


@responses.activate
def test_a_card_with_one_variant_offers_add_to_wishlist_for_it(ash_client, ash):
    responses.get(CARD_URL, json=detail(variants={"holo": True}))

    html = wish(ash_client, "holo").content.decode()

    assert Wish.objects.get(user=ash).variant.variant == "holo"
    assert "On your wishlist: Holo" in html


@responses.activate
def test_wishing_again_for_the_same_card_and_variant_does_not_add_a_second_wish(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    wish(ash_client, "reverse")

    again = wish(ash_client, "reverse").content.decode()

    assert Wish.objects.filter(user=ash).count() == 1
    assert "Reverse holo is already on your wishlist." in again


@responses.activate
def test_the_nav_counts_only_my_active_wishes_and_updates_after_a_tile_wish(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    make_wish(ash, "sv03.5-001", "Bulbasaur")
    make_wish(ash, "sv03.5-004", "Charmander", "reverse")
    make_wish(ash, "sv03.5-007", "Squirtle", fulfilled_at=timezone.now())  # fulfilled: not counted
    make_wish(make_user("misty"), "sv03.5-120", "Starmie")  # someone else's: not counted

    page = ash_client.get(reverse("home")).content.decode()
    tile = wish(ash_client, "reverse").content.decode()

    assert nav_wish_count(page) == 2
    assert nav_wish_count(tile) == 3


def test_removing_a_wish_deletes_my_own_but_another_users_is_a_404_and_kept(ash_client, ash):
    mine = make_wish(ash, "sv03.5-001", "Bulbasaur", "reverse")
    mistys = make_wish(make_user("misty"), "sv03.5-120", "Starmie")

    removed = ash_client.post(reverse("collection:wish_remove", args=[mine.pk]))
    blocked = ash_client.post(reverse("collection:wish_remove", args=[mistys.pk]))

    assert removed.status_code in (200, 302)
    assert not Wish.objects.filter(pk=mine.pk).exists()
    assert blocked.status_code == 404
    assert Wish.objects.filter(pk=mistys.pk).exists()


@responses.activate
def test_wishing_for_a_card_new_locally_stores_it_and_rejects_variants_it_lacks(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)

    rejected = wish(ash_client, "holo").content.decode()
    wish(ash_client, "reverse")

    assert "come in that variant" in rejected
    card = Card.objects.get(tcgdex_id="sv03.5-025")
    assert sorted(card.variants.values_list("variant", flat=True)) == ["normal", "reverse"]
    assert CardVariant.objects.get(card=card, variant="reverse").market_price == Decimal("0.70")
    assert [w.variant.variant for w in Wish.objects.filter(user=ash)] == ["reverse"]


@responses.activate  # no URLs registered: any TCGdex request would fail the test
def test_wishing_while_tcgdex_is_down_for_an_unstored_card_says_so_and_saves_nothing(ash_client):
    cache.set(tcgdex.OUTAGE_KEY, timezone.now().timestamp() + 60, 60)

    html = wish(ash_client, "normal").content.decode()

    assert "add this card to your wishlist because TCGdex" in html
    assert not Wish.objects.exists()
    assert len(responses.calls) == 0


@responses.activate  # no URLs registered: any TCGdex request would fail the test
def test_the_wishlist_lists_only_my_wishes_newest_first_while_tcgdex_is_down(ash_client, ash):
    cache.set(tcgdex.OUTAGE_KEY, timezone.now().timestamp() + 60, 60)
    make_wish(ash, "sv03.5-001", "Bulbasaur", "reverse", price="0.45", notes="for my binder")
    make_wish(ash, "sv03.5-004", "Charmander")
    make_wish(ash, "sv03.5-007", "Squirtle", fulfilled_at=timezone.now())
    make_wish(make_user("misty"), "sv03.5-120", "Starmie")

    response = ash_client.get(reverse("collection:wishlist"))

    html = response.content.decode()
    assert response.status_code == 200
    assert len(responses.calls) == 0
    assert html.index("Charmander") < html.index("Bulbasaur")  # newest first
    assert "Normal" in html and "Reverse holo" in html
    assert "$0.45" in html and "for my binder" in html
    # The fulfilled wish is listed apart, above the active ones.
    assert html.index("Got it</h2>") < html.index("Squirtle") < html.index("Charmander")
    assert "Starmie" not in html


def test_removing_a_wish_with_htmx_shows_a_notice_and_the_new_nav_count(ash_client, ash):
    mine = make_wish(ash, "sv03.5-001", "Bulbasaur")
    make_wish(ash, "sv03.5-004", "Charmander")

    response = ash_client.post(
        reverse("collection:wish_remove", args=[mine.pk]), headers={"HX-Request": "true"}
    )

    html = response.content.decode()
    assert "<html" not in html
    assert "Removed Bulbasaur (Normal) from your wishlist." in html
    assert nav_wish_count(html) == 1


def remove_wish(client, wish):
    return client.post(
        reverse("collection:wish_remove", args=[wish.pk]), headers={"HX-Request": "true"}
    )


def undo_wish(client, wish):
    return client.post(
        reverse("collection:wish_undo", args=[wish.pk]), headers={"HX-Request": "true"}
    )


def test_undo_puts_a_removed_wish_back_with_its_notes_and_date(ash_client, ash):
    wish_ = make_wish(ash, "sv03.5-001", "Bulbasaur", "reverse", notes="for my binder")
    Wish.objects.filter(pk=wish_.pk).update(created=timezone.now() - timedelta(days=3))
    created = Wish.objects.get(pk=wish_.pk).created

    removed = remove_wish(ash_client, wish_).content.decode()
    html = undo_wish(ash_client, wish_).content.decode()

    assert reverse("collection:wish_undo", args=[wish_.pk]) in removed
    restored = Wish.objects.get(user=ash)
    assert (restored.variant, restored.notes, restored.created) == (
        wish_.variant,
        "for my binder",
        created,
    )
    assert "Put it back on your wishlist." in html and "Bulbasaur" in html
    assert nav_wish_count(html) == 1


def test_wish_undo_works_only_once_and_not_on_another_users_removal(ash_client, ash, client):
    wish_ = make_wish(ash, "sv03.5-001", "Bulbasaur")
    remove_wish(ash_client, wish_)
    undo_wish(ash_client, wish_)

    again = undo_wish(ash_client, wish_).content.decode()
    client.force_login(make_user("misty"))  # misty's session has no record of ash's removal
    mistys_try = undo_wish(client, wish_).content.decode()

    assert "can no longer be undone" in again
    assert "can no longer be undone" in mistys_try
    assert Wish.objects.count() == 1


def test_undo_keeps_a_wish_made_again_since_the_removal(ash_client, ash):
    wish_ = make_wish(ash, "sv03.5-001", "Bulbasaur", notes="old note")
    remove_wish(ash_client, wish_)
    make_wish(ash, "sv03.5-001", "Bulbasaur", notes="new note")

    undo_wish(ash_client, wish_)

    assert list(Wish.objects.filter(user=ash).values_list("notes", flat=True)) == ["new note"]
