from datetime import UTC, datetime

import pytest
import responses
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from catalog import tcgdex
from catalog.models import Card
from collection.models import OwnedCard
from collection.tests.helpers import make_owned, make_user


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


@pytest.mark.parametrize("action", ["entry_add", "entry_remove", "entry_delete"])
def test_actions_on_another_users_entry_return_404_and_change_nothing(ash_client, action):
    mistys = make_owned(make_user("misty"), "sv03.5-120", "Starmie", price="1.00", quantity=2)

    response = ash_client.post(reverse(f"collection:{action}", args=[mistys.pk]))

    assert response.status_code == 404
    assert OwnedCard.objects.get(pk=mistys.pk).quantity == 2


@responses.activate  # no URLs registered: any TCGdex request would fail the test
def test_the_page_lists_entries_newest_first_from_local_data_while_tcgdex_is_down(ash_client, ash):
    cache.set(tcgdex.OUTAGE_KEY, timezone.now().timestamp() + 60, 60)
    make_owned(ash, "sv03.5-006", "Charizard", "holo", price=None)
    make_owned(
        ash,
        "sv03.5-025",
        "Pikachu",
        "reverse",
        price="0.70",
        quantity=3,
        updated=datetime(2026, 11, 10, tzinfo=UTC),
    )

    response = ash_client.get(reverse("collection:index"))

    html = response.content.decode()
    assert response.status_code == 200
    assert len(responses.calls) == 0
    assert html.index("Pikachu") < html.index("Charizard")  # newest first
    assert "Reverse holo" in html and "3 owned" in html
    assert "$0.70" in html and "as of Nov 10, 2026" in html
    assert "$2.10" in html  # entry value and collection total
    assert "No price" in html
    assert "1 card has no price" in html


def post(client, action, entry):
    return client.post(reverse(f"collection:{action}", args=[entry.pk]), HTTP_HX_REQUEST="true")


def test_plus_and_minus_step_the_entry_and_update_the_total(ash_client, ash):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.50")

    plus = post(ash_client, "entry_add", entry).content.decode()

    assert "<html" not in plus  # a fragment
    assert "2 owned" in plus and "Added 1 Normal." in plus
    assert 'id="collection-value"' in plus and 'hx-swap-oob="true"' in plus
    assert "$1.00" in plus  # entry value and the new total
    minus = post(ash_client, "entry_remove", entry).content.decode()
    assert "1 owned" in minus and "Removed 1 Normal." in minus
    assert OwnedCard.objects.get(pk=entry.pk).quantity == 1


def test_minus_on_the_last_copy_deletes_the_entry(ash_client, ash):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.50")

    html = post(ash_client, "entry_remove", entry).content.decode()

    assert "Removed your last Normal copy." in html
    assert "owned" not in html.split('id="collection-value"')[0]  # no stepper left
    assert not OwnedCard.objects.filter(pk=entry.pk).exists()
    assert Card.objects.filter(tcgdex_id="sv03.5-025").exists()  # shared card is kept


def test_remove_deletes_every_copy_and_updates_the_total(ash_client, ash):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.50", quantity=4)
    make_owned(ash, "sv03.5-006", "Charizard", "holo", price="3.00")

    html = post(ash_client, "entry_delete", entry).content.decode()

    assert "Removed Pikachu (Normal) from your collection." in html
    assert "$3.00" in html  # total without Pikachu
    assert not OwnedCard.objects.filter(pk=entry.pk).exists()


def test_without_htmx_an_action_returns_to_the_collection_page(ash_client, ash):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.50")

    response = ash_client.post(reverse("collection:entry_add", args=[entry.pk]))

    assert response.status_code == 302
    assert response.url == reverse("collection:index")
    assert OwnedCard.objects.get(pk=entry.pk).quantity == 2


def test_another_users_entries_are_not_listed(ash_client):
    make_owned(make_user("misty"), "sv03.5-120", "Starmie", price="1.00")

    html = ash_client.get(reverse("collection:index")).content.decode()

    assert "Starmie" not in html
    assert "Your collection is empty." in html


def test_entry_value_is_shown_as_currency(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.70", quantity=3)

    html = ash_client.get(reverse("collection:index")).content.decode()

    assert "Total Value: <span" in html
    assert "$2.10</span>" in html
    assert "2.0999" not in html and "2.1000" not in html


def undo(client, entry):
    return client.post(reverse("collection:entry_undo", args=[entry.pk]), HTTP_HX_REQUEST="true")


def test_minus_offers_undo_which_puts_the_copy_back(ash_client, ash):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.50", quantity=2)

    minus = post(ash_client, "entry_remove", entry).content.decode()
    assert reverse("collection:entry_undo", args=[entry.pk]) in minus
    html = undo(ash_client, entry).content.decode()

    assert OwnedCard.objects.get(pk=entry.pk).quantity == 2
    assert "2 owned" in html and "Put back 1 Normal." in html
    assert "$1.00" in html  # the total is back too


@pytest.mark.parametrize("action", ["entry_remove", "entry_delete"])
def test_undo_after_deleting_restores_the_entry_with_its_notes_and_date(ash_client, ash, action):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.50", quantity=1)
    OwnedCard.objects.filter(pk=entry.pk).update(notes="first pull")
    entry.refresh_from_db()
    newer = make_owned(ash, "sv03.5-006", "Charizard", "holo", price="3.00")

    html = post(ash_client, action, entry).content.decode()
    assert reverse("collection:entry_undo", args=[entry.pk]) in html
    undo(ash_client, entry)

    restored = OwnedCard.objects.get(user=ash, variant=entry.variant)
    assert (restored.quantity, restored.notes, restored.created) == (1, "first pull", entry.created)
    page = ash_client.get(reverse("collection:index")).content.decode()
    assert page.index("Charizard") < page.index("Pikachu")  # back in its old place
    assert newer.pk != restored.pk


def test_undo_works_only_once(ash_client, ash):
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "normal", quantity=2)
    post(ash_client, "entry_remove", entry)

    undo(ash_client, entry)
    again = undo(ash_client, entry).content.decode()

    assert OwnedCard.objects.get(pk=entry.pk).quantity == 2
    assert "can no longer be undone" in again
