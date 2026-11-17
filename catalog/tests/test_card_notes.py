"""Notes on the card detail page: each variant's collection entry note and wish note."""

import pytest
import responses
from django.urls import reverse

from catalog import tcgdex
from catalog.tests.test_card_detail import detail
from collection.tests.helpers import make_owned, make_user, make_wish

CARD_URL = f"{tcgdex.BASE_URL}/cards/sv03.5-025"
PRICES = {"unit": "USD", "normal": {"marketPrice": 0.28}, "reverse-holofoil": {"marketPrice": 0.7}}
PIKACHU = detail(variants={"normal": True, "reverse": True}, tcgplayer=PRICES)
CARD_PAGE = reverse("catalog:card_detail", args=["sv03.5-025"])
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


@responses.activate
def test_the_card_page_shows_the_users_entry_and_wish_notes_with_their_controls(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    owned.notes = "Pulled from my first booster box"
    owned.save()
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse", notes="Trade target")
    misty = make_user("misty")
    make_wish(misty, "sv03.5-025", "Pikachu", "normal", notes="Misty's secret")

    html = ash_client.get(CARD_PAGE).content.decode()

    assert "Pulled from my first booster box" in html
    assert "Trade target" in html
    assert "Misty's secret" not in html
    # Each note's controls point at the existing notes actions, flagged as from the card page.
    entry_notes = reverse("collection:entry_notes", args=[owned.pk])
    wish_notes = reverse("collection:wish_notes", args=[wish.pk])
    assert f'hx-get="{entry_notes}?from=card"' in html
    assert f'hx-get="{wish_notes}?from=card"' in html
    assert f'id="note-entry-{owned.pk}"' in html
    assert f'id="note-wish-{wish.pk}"' in html


def test_saving_a_note_from_the_card_page_returns_just_that_note_area(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    url = reverse("collection:entry_notes", args=[owned.pk]) + "?from=card"

    response = ash_client.post(url, {"notes": "Pulled from my first booster box"}, **HTMX)

    html = response.content.decode()
    owned.refresh_from_db()
    assert owned.notes == "Pulled from my first booster box"
    assert html.lstrip().startswith(f'<div id="note-entry-{owned.pk}"')  # only the note area
    assert "Pulled from my first booster box" in html and "Note saved." in html
    assert f'id="entry-{owned.pk}"' not in html  # not the collection page's entry card
    assert "owned</span>" not in html  # nor its stepper


def test_without_htmx_saving_or_deleting_a_note_from_the_card_page_returns_to_it(ash_client, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse", notes="Trade target")
    notes_url = reverse("collection:wish_notes", args=[wish.pk]) + "?from=card"
    delete_url = reverse("collection:wish_notes_delete", args=[wish.pk]) + "?from=card"

    saved = ash_client.post(notes_url, {"notes": "Second copy for a binder"})
    wish.refresh_from_db()
    assert wish.notes == "Second copy for a binder"
    assert saved.status_code == 302 and saved.url == CARD_PAGE

    deleted = ash_client.post(delete_url)
    wish.refresh_from_db()
    assert wish.notes == ""
    assert deleted.status_code == 302 and deleted.url == CARD_PAGE


def test_the_edit_form_and_cancel_from_the_card_page_return_just_the_note_area(ash_client, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", "reverse", notes="Trade target")
    url = reverse("collection:wish_notes", args=[wish.pk]) + "?from=card"

    editing = ash_client.get(url, **HTMX).content.decode()
    cancelled = ash_client.get(url + "&cancel=1", **HTMX).content.decode()

    assert editing.lstrip().startswith(f'<div id="note-wish-{wish.pk}"')
    assert "<textarea" in editing and "Trade target" in editing
    assert f'hx-get="{url}&cancel=1"' in editing  # Cancel keeps the card page flag
    assert f'id="wish-{wish.pk}"' not in editing  # not the wishlist page's wish card
    assert cancelled.lstrip().startswith(f'<div id="note-wish-{wish.pk}"')
    assert "<textarea" not in cancelled and "Trade target" in cancelled


@pytest.mark.parametrize(
    "notes, error",
    [
        ("   ", "Write a note, or use Delete note to remove it."),
        ("x" * 501, "Notes can be at most 500 characters; this one has 501."),
    ],
    ids=["blank", "too-long"],
)
def test_an_invalid_note_from_the_card_page_shows_the_error_in_the_note_area(
    ash_client, ash, notes, error
):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    owned.notes = "Pulled from my first booster box"
    owned.save()
    url = reverse("collection:entry_notes", args=[owned.pk]) + "?from=card"

    html = ash_client.post(url, {"notes": notes}, **HTMX).content.decode()

    owned.refresh_from_db()
    assert owned.notes == "Pulled from my first booster box"  # nothing saved
    assert html.lstrip().startswith(f'<div id="note-entry-{owned.pk}"')
    assert error in html and "<textarea" in html


def test_deleting_a_note_from_the_card_page_returns_just_the_note_area(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    owned.notes = "Pulled from my first booster box"
    owned.save()
    url = reverse("collection:entry_notes_delete", args=[owned.pk]) + "?from=card"

    html = ash_client.post(url, **HTMX).content.decode()

    owned.refresh_from_db()
    assert owned.notes == ""
    assert html.lstrip().startswith(f'<div id="note-entry-{owned.pk}"')
    assert "Note deleted." in html and "Add note" in html


@pytest.mark.parametrize(
    "make_item, edit_url, delete_url",
    [
        (make_owned, "collection:entry_notes", "collection:entry_notes_delete"),
        (make_wish, "collection:wish_notes", "collection:wish_notes_delete"),
    ],
    ids=["entry", "wish"],
)
def test_another_users_note_is_a_404_from_the_card_page(
    ash_client, make_item, edit_url, delete_url
):
    item = make_item(make_user("misty"), "sv03.5-025", "Pikachu")

    for response in (
        ash_client.get(reverse(edit_url, args=[item.pk]) + "?from=card", **HTMX),
        ash_client.post(reverse(edit_url, args=[item.pk]) + "?from=card", {"notes": "Mine"}),
        ash_client.post(reverse(delete_url, args=[item.pk]) + "?from=card", **HTMX),
    ):
        assert response.status_code == 404


def test_the_note_form_page_from_the_card_page_links_back_to_it(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    owned.notes = "Pulled from my first booster box"
    owned.save()

    html = ash_client.get(
        reverse("collection:entry_notes", args=[owned.pk]) + "?from=card"
    ).content.decode()

    assert f'href="{CARD_PAGE}" class="btn btn-ghost">Cancel' in html
    delete_url = reverse("collection:entry_notes_delete", args=[owned.pk])
    assert f'action="{delete_url}?from=card"' in html


def test_minus_on_the_last_copy_removes_that_entrys_note_from_the_card_page(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", "normal")
    owned.notes = "Pulled from my first booster box"
    owned.save()

    html = ash_client.post(
        reverse("catalog:card_remove", args=["sv03.5-025"]), {"variant": "normal"}, **HTMX
    ).content.decode()

    assert f'id="note-entry-{owned.pk}"' not in html
    assert "Pulled from my first booster box" not in html
