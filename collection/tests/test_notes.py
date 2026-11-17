import pytest
from django.urls import reverse
from django.utils import timezone

from collection.tests.helpers import make_owned, make_user, make_wish

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def test_a_collection_note_over_500_characters_is_rejected_and_nothing_is_saved(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    owned.notes = "Pulled from my first booster box"
    owned.save()

    response = ash_client.post(
        reverse("collection:entry_notes", args=[owned.pk]), {"notes": "x" * 501}, **HTMX
    )

    owned.refresh_from_db()
    assert owned.notes == "Pulled from my first booster box"
    assert "Notes can be at most 500 characters; this one has 501." in response.content.decode()


def test_a_blank_wish_note_is_rejected_and_delete_note_clears_it(ash_client, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", notes="Trade target")

    blank = ash_client.post(
        reverse("collection:wish_notes", args=[wish.pk]), {"notes": "   "}, **HTMX
    )

    wish.refresh_from_db()
    assert wish.notes == "Trade target"
    assert "Write a note, or use Delete note to remove it." in blank.content.decode()

    ash_client.post(reverse("collection:wish_notes_delete", args=[wish.pk]), **HTMX)

    wish.refresh_from_db()
    assert wish.notes == ""


@pytest.mark.parametrize(
    "make_item, edit_url, delete_url",
    [
        (make_owned, "collection:entry_notes", "collection:entry_notes_delete"),
        (make_wish, "collection:wish_notes", "collection:wish_notes_delete"),
    ],
    ids=["entry", "wish"],
)
def test_another_users_note_cannot_be_edited_or_deleted(
    ash_client, make_item, edit_url, delete_url
):
    item = make_item(make_user("misty"), "sv03.5-025", "Pikachu")
    item.notes = "Misty's note"
    item.save()

    responses = [
        ash_client.get(reverse(edit_url, args=[item.pk]), **HTMX),
        ash_client.post(reverse(edit_url, args=[item.pk]), {"notes": "Ash was here"}, **HTMX),
        ash_client.post(reverse(delete_url, args=[item.pk]), **HTMX),
    ]

    item.refresh_from_db()
    assert [response.status_code for response in responses] == [404, 404, 404]
    assert item.notes == "Misty's note"


def test_a_collection_note_can_be_added_then_edited_in_place(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    url = reverse("collection:entry_notes", args=[owned.pk])

    form = ash_client.get(url, **HTMX).content.decode()
    ash_client.post(url, {"notes": "Pulled from my first booster box"}, **HTMX)
    edited = ash_client.post(url, {"notes": "  Trade target  "}, **HTMX).content.decode()

    owned.refresh_from_db()
    edit_form = ash_client.get(url, **HTMX).content.decode()
    assert 'name="notes"' in form and "Save note" in form
    assert "Delete note" not in form  # nothing to delete yet
    assert "Delete note" in edit_form and 'name="notes"' in edit_form
    assert owned.notes == "Trade target"
    assert f'id="entry-{owned.pk}"' in edited  # the whole entry comes back, with its note
    assert "Trade target" in edited and "Note saved." in edited
    assert "Edit note" in edited and "Delete note" in edited


def test_a_wish_note_can_be_added_and_shows_on_the_wishlist(ash_client, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu")
    before = ash_client.get(reverse("collection:wishlist")).content.decode()

    ash_client.post(
        reverse("collection:wish_notes", args=[wish.pk]), {"notes": "Ask at league night"}, **HTMX
    )

    after = ash_client.get(reverse("collection:wishlist")).content.decode()
    assert "Add note" in before
    assert "Ask at league night" in after and "Edit note" in after


def test_a_fulfilled_wish_note_can_be_edited(ash_client, ash):
    wish = make_wish(ash, "sv03.5-025", "Pikachu", fulfilled_at=timezone.now())

    ash_client.post(
        reverse("collection:wish_notes", args=[wish.pk]), {"notes": "Got it at a trade"}, **HTMX
    )

    wish.refresh_from_db()
    assert wish.notes == "Got it at a trade"


def test_cancel_returns_the_entry_without_the_form(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")

    html = ash_client.get(
        reverse("collection:entry_notes", args=[owned.pk]), {"cancel": "1"}, **HTMX
    ).content.decode()

    assert 'name="notes"' not in html and "Add note" in html


def test_notes_are_shown_as_escaped_plain_text(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    owned.notes = "<script>alert(1)</script> & <b>bold</b>"
    owned.save()

    html = ash_client.get(reverse("collection:index")).content.decode()

    assert "<script>alert(1)</script>" not in html and "<b>bold</b>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;b&gt;bold&lt;/b&gt;" in html


def test_without_htmx_the_note_form_is_a_page_and_saving_returns_to_the_list(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")
    url = reverse("collection:entry_notes", args=[owned.pk])

    page = ash_client.get(url).content.decode()
    too_long = ash_client.post(url, {"notes": "x" * 501}).content.decode()
    saved = ash_client.post(url, {"notes": "Binder page 3"})
    with_note = ash_client.get(url).content.decode()
    deleted = ash_client.post(reverse("collection:entry_notes_delete", args=[owned.pk]))

    assert "Note on Pikachu" in page and "<html" in page
    assert "Delete note" not in page
    assert "Delete note" in with_note  # once there is a note
    assert "Notes can be at most 500 characters; this one has 501." in too_long
    assert saved.status_code == 302 and saved.url == reverse("collection:index")
    assert deleted.status_code == 302
    owned.refresh_from_db()
    assert owned.notes == ""


def test_editing_notes_requires_sign_in(client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu")

    response = client.post(reverse("collection:entry_notes", args=[owned.pk]), {"notes": "hi"})

    assert response.status_code == 302 and "/accounts/login/" in response.url
    owned.refresh_from_db()
    assert owned.notes == ""
