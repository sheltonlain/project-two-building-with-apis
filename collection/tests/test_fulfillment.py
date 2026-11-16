"""Wish fulfillment: adding a copy fulfills a matching wish; "−", Keep and OK undo or dismiss it."""

import re
from datetime import UTC, datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from collection import services
from collection.models import OwnedCard, Wish
from collection.tests.helpers import make_owned, make_user, make_variant, make_wish


@pytest.fixture
def ash(db):
    return make_user("ash")


def test_adding_a_copy_fulfills_only_the_wish_for_that_exact_variant(ash):
    make_variant("sv03.5-025", "Pikachu", "normal")
    reverse_wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    normal_wish = make_wish(ash, "sv03.5-025", "Pikachu", "normal")

    owned = services.add_copy(ash, "sv03.5-025", "normal")

    normal_wish.refresh_from_db()
    reverse_wish.refresh_from_db()
    assert normal_wish.fulfilled_at is not None
    assert normal_wish.fulfilled_by == owned
    assert reverse_wish.fulfilled_at is None
    assert reverse_wish.fulfilled_by is None

    # A second copy has no active wish left to fulfill.
    services.add_copy(ash, "sv03.5-025", "normal")
    assert Wish.objects.filter(fulfilled_at__isnull=False).count() == 1


def test_removing_a_copy_restores_the_most_recently_fulfilled_wish_even_for_the_last_copy(ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", quantity=2)
    older = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=datetime(2026, 11, 1, tzinfo=UTC))
    newer = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=datetime(2026, 11, 9, tzinfo=UTC))
    Wish.objects.update(fulfilled_by=owned)

    services.remove_copy(owned)

    newer.refresh_from_db()
    older.refresh_from_db()
    assert (newer.fulfilled_at, newer.fulfilled_by) == (None, None)
    assert older.fulfilled_by == owned

    # The user drops the restored wish; "−" on the last copy deletes the entry and restores
    # the older wish.
    services.remove_wish(newer)
    assert services.remove_copy(owned) is None

    older.refresh_from_db()
    assert (older.fulfilled_at, older.fulfilled_by) == (None, None)


def test_keep_reopens_a_fulfilled_wish_and_ok_deletes_it_while_the_copies_stay(ash):
    make_variant("sv03.5-025", "Pikachu", "normal")
    make_variant("sv03.5-025", "Pikachu", "reverse")
    kept = make_wish(ash, "sv03.5-025", "Pikachu", "normal")
    dismissed = make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    normal = services.add_copy(ash, "sv03.5-025", "normal")
    reverse = services.add_copy(ash, "sv03.5-025", "reverse")

    services.keep_wish(Wish.objects.get(pk=kept.pk))
    services.dismiss_wish(Wish.objects.get(pk=dismissed.pk))

    kept.refresh_from_db()
    assert (kept.fulfilled_at, kept.fulfilled_by) == (None, None)
    assert not Wish.objects.filter(pk=dismissed.pk).exists()
    normal.refresh_from_db()
    reverse.refresh_from_db()
    assert (normal.quantity, reverse.quantity) == (1, 1)

    # Keep when the user has wished for that variant again since: the newer wish stays the
    # only active one and the fulfilled one goes.
    services.add_copy(ash, "sv03.5-025", "normal")  # fulfills `kept` again
    again = make_wish(ash, "sv03.5-025", "Pikachu", "normal", notes="second copy")
    services.keep_wish(Wish.objects.get(pk=kept.pk))

    assert list(services.active_wishes(ash)) == [again]
    assert not Wish.objects.filter(pk=kept.pk).exists()


def test_restoring_a_wish_the_user_has_made_again_deletes_the_fulfilled_one(ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    old = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=datetime(2026, 11, 1, tzinfo=UTC))
    Wish.objects.update(fulfilled_by=owned)
    again = make_wish(ash, "sv03.5-025", "Pikachu", notes="another one")

    services.remove_copy(owned)

    assert list(services.active_wishes(ash)) == [again]
    assert not Wish.objects.filter(pk=old.pk).exists()


# --- Web views ---------------------------------------------------------------------------------


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def nav_counts(html):
    """(active, fulfilled) from the nav badges (or their out-of-band updates)."""
    active = re.search(r'id="nav-wish-count"[^>]*>\s*(\d+)\s*<', html)
    fulfilled = re.search(r'id="nav-fulfilled-count"[^>]*>\s*✓ (\d+)\s*<', html)
    return int(active.group(1)), int(fulfilled.group(1))


HTMX = {"HTTP_HX_REQUEST": "true"}


def test_a_tile_add_that_fulfills_a_wish_says_so_and_links_to_the_wishlist(ash_client, ash):
    make_variant("sv03.5-025", "Pikachu", "reverse")
    make_wish(ash, "sv03.5-025", "Pikachu", "normal")
    url = reverse("catalog:tile_add", args=["sv03.5-025"])

    reverse_html = ash_client.post(url, {"variant": "reverse"}, **HTMX).content.decode()
    normal_html = ash_client.post(url, {"variant": "normal"}, **HTMX).content.decode()

    assert "fulfilled a wish" not in reverse_html
    assert "Added 1 Normal. That fulfilled a wish." in normal_html
    assert reverse("collection:wishlist") + '" class="link">View on wishlist' in normal_html
    assert 'hx-boost="false"' in normal_html  # the link opens the page, not a swap into the tile
    assert nav_counts(normal_html) == (0, 1)


def test_minus_on_a_tile_brings_the_wish_back_and_updates_the_nav(ash_client, ash):
    make_wish(ash, "sv03.5-025", "Pikachu")
    ash_client.post(reverse("catalog:tile_add", args=["sv03.5-025"]), {"variant": "normal"})

    response = ash_client.post(
        reverse("catalog:tile_remove", args=["sv03.5-025"]), {"variant": "normal"}, **HTMX
    )

    html = response.content.decode()
    assert "Removed your last Normal copy. Its wish is back on your wishlist." in html
    assert nav_counts(html) == (1, 0)
    assert services.active_wishes(ash).count() == 1


def test_got_it_adds_the_wished_variant_and_shows_the_wish_crossed_out(ash_client, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse")

    response = ash_client.post(reverse("collection:wish_got_it", args=[wish.pk]), **HTMX)

    html = response.content.decode()
    wish.refresh_from_db()
    owned = OwnedCard.objects.get(user=ash)
    assert (owned.variant.variant, owned.quantity) == ("reverse", 1)
    assert wish.fulfilled_by == owned
    assert "line-through" in html and "Fulfilled " in html
    # The whole wishlist comes back, with the wish moved under Got it and its notice on it.
    assert html.index("Got it</h2>") < html.index(f'id="wish-{wish.pk}"')
    assert "Added 1 Reverse holo to your collection." in html
    assert "No active wishes." in html
    assert "Keep it on my wishlist" in html and ">OK</button>" in html
    assert nav_counts(html) == (0, 1)


def test_the_wishlist_shows_fulfilled_wishes_with_keep_and_ok_and_the_nav_counts_them(
    ash_client, ash
):
    make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=datetime(2026, 11, 14, tzinfo=UTC))
    make_wish(ash, "sv03.5-004", "Charmander")

    html = ash_client.get(reverse("collection:wishlist")).content.decode()

    assert "Fulfilled Nov 14, 2026" in html
    assert html.count("Keep it on my wishlist") == 1
    assert html.count(">Got it</button>") == 1  # only on the active wish
    assert nav_counts(html) == (1, 1)


def test_keep_and_ok_from_the_wishlist(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    keep = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=timezone.now())
    ok = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=timezone.now())
    Wish.objects.update(fulfilled_by=owned)

    ok_html = ash_client.post(reverse("collection:wish_dismiss", args=[ok.pk]), **HTMX)
    keep_html = ash_client.post(reverse("collection:wish_keep", args=[keep.pk]), **HTMX)

    ok_html = ok_html.content.decode()
    # The notice sits above the lists, since the wish is gone; the other one is still under Got it.
    assert ok_html.index("Dismissed Pikachu (Normal).") < ok_html.index("Got it</h2>")
    assert f'id="wish-{ok.pk}"' not in ok_html and f'id="wish-{keep.pk}"' in ok_html
    keep_html = keep_html.content.decode()
    # Keep returns the whole wishlist: the wish is back in the active list, not under Got it.
    assert 'id="wishlist-body"' in keep_html
    assert "Got it</h2>" not in keep_html
    assert "Keep it on my wishlist" not in keep_html
    assert "1 wish</p>" in keep_html and "Kept on your wishlist." in keep_html
    assert nav_counts(keep_html) == (1, 0)
    assert list(services.active_wishes(ash)) == [keep]
    assert not Wish.objects.filter(pk=ok.pk).exists()
    assert OwnedCard.objects.get(pk=owned.pk).quantity == 1


def test_wish_actions_on_another_users_wish_or_the_wrong_state_are_404(ash_client, ash):
    misty = make_user("misty")
    mine_active = make_wish(ash, "sv03.5-025", "Pikachu")
    theirs_active = make_wish(misty, "sv03.5-025", "Pikachu")
    theirs_fulfilled = make_wish(misty, "sv03.5-004", "Charmander", fulfilled_at=timezone.now())

    def post(name, wish):
        return ash_client.post(reverse(f"collection:{name}", args=[wish.pk])).status_code

    assert post("wish_got_it", theirs_active) == 404
    assert post("wish_keep", theirs_fulfilled) == 404
    assert post("wish_dismiss", theirs_fulfilled) == 404
    assert post("wish_keep", mine_active) == 404  # Keep and OK are for fulfilled wishes only
    assert post("wish_dismiss", mine_active) == 404
    assert not OwnedCard.objects.exists()
    assert Wish.objects.filter(fulfilled_at__isnull=True).count() == 2
    assert Wish.objects.filter(pk=theirs_fulfilled.pk).exists()


def test_collection_minus_restores_the_wish_and_undo_fulfills_it_again(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    fulfilled_at = datetime(2026, 11, 14, tzinfo=UTC)
    wish = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=fulfilled_at)
    Wish.objects.update(fulfilled_by=owned)

    minus = ash_client.post(reverse("collection:entry_remove", args=[owned.pk]), **HTMX)
    wish.refresh_from_db()
    assert wish.fulfilled_at is None
    assert "Its wish is back on your wishlist." in minus.content.decode()
    assert nav_counts(minus.content.decode()) == (1, 0)

    undo = ash_client.post(reverse("collection:entry_undo", args=[owned.pk]), **HTMX)

    wish.refresh_from_db()
    restored = OwnedCard.objects.get(user=ash)
    assert (wish.fulfilled_at, wish.fulfilled_by) == (fulfilled_at, restored)
    assert nav_counts(undo.content.decode()) == (0, 1)
