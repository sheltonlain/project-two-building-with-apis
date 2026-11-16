import pytest
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalog import tcgdex
from catalog.models import Card
from catalog.tests.test_card_detail import detail
from collection.models import OwnedCard

CARD_URL = f"{tcgdex.BASE_URL}/cards/sv03.5-025"
PRICES = {"unit": "USD", "normal": {"marketPrice": 0.28}, "reverse-holofoil": {"marketPrice": 0.7}}
PIKACHU = detail(variants={"normal": True, "reverse": True}, tcgplayer=PRICES)


def make_user(username):
    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def details(client, variant=None):
    params = {"variant": variant} if variant else {}
    return client.get(reverse("catalog:tile_details", args=["sv03.5-025"]), params)


def add(client, variant="normal"):
    return client.post(reverse("catalog:tile_add", args=["sv03.5-025"]), {"variant": variant})


def remove(client, variant="normal"):
    return client.post(reverse("catalog:tile_remove", args=["sv03.5-025"]), {"variant": variant})


@responses.activate
def test_an_unowned_card_offers_add_to_collection(ash_client):
    responses.get(CARD_URL, json=PIKACHU)

    html = details(ash_client).content.decode()

    assert "Add to collection" in html
    assert "owned" not in html
    assert "You own" not in html


@responses.activate
def test_adding_turns_the_button_into_a_stepper_with_a_summary_and_confirmation(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)

    response = add(ash_client, "reverse")

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html  # a tile fragment
    assert "Add to collection" not in html
    assert "1 owned" in html
    assert "You own: 1 Reverse holo" in html
    assert "Added 1 Reverse holo." in html
    assert '<option value="reverse" selected>Reverse holo</option>' in html  # keeps the variant
    assert "$0.70" in html
    assert OwnedCard.objects.get(user=ash).quantity == 1


@responses.activate
def test_plus_and_minus_step_the_quantity_and_zero_brings_back_the_add_button(ash_client, ash):
    responses.get(CARD_URL, json=PIKACHU)
    add(ash_client)

    plus = add(ash_client).content.decode()
    minus = remove(ash_client).content.decode()
    last = remove(ash_client).content.decode()

    assert "2 owned" in plus
    assert "1 owned" in minus and "Removed 1 Normal." in minus
    assert "Add to collection" in last
    assert "Removed your last Normal copy." in last
    assert "You own" not in last
    assert not OwnedCard.objects.exists()
    assert Card.objects.filter(tcgdex_id="sv03.5-025").exists()


@responses.activate
def test_the_summary_lists_every_owned_variant_and_switching_shows_that_variants_count(
    ash_client,
):
    responses.get(CARD_URL, json=PIKACHU)
    add(ash_client, "reverse")
    add(ash_client, "normal")
    add(ash_client, "normal")

    normal = details(ash_client, "normal").content.decode()
    reverse_ = details(ash_client, "reverse").content.decode()

    assert "You own: 2 Normal, 1 Reverse holo" in normal
    assert "2 owned" in normal and "$0.28" in normal
    assert "1 owned" in reverse_ and "$0.70" in reverse_
    assert """hx-vals='{"variant": "reverse"}'""" in reverse_  # buttons act on that variant


@responses.activate
def test_adding_a_variant_the_card_does_not_have_shows_a_message_and_saves_nothing(ash_client):
    responses.get(CARD_URL, json=PIKACHU)

    html = add(ash_client, "holo").content.decode()

    assert "doesn&#x27;t come in that variant" in html
    assert "Add to collection" in html
    assert not OwnedCard.objects.exists()


@responses.activate
def test_steps_on_a_stored_card_work_while_tcgdex_is_down(ash_client):
    responses.get(CARD_URL, json=PIKACHU)
    add(ash_client)
    responses.replace(responses.GET, CARD_URL, status=503)
    tcgdex.cache.clear()  # no cached detail, and the breaker is open
    tcgdex.cache.set(tcgdex.OUTAGE_KEY, 1e12, tcgdex.OUTAGE_SECONDS)

    html = add(ash_client).content.decode()

    assert "2 owned" in html
    assert len(responses.calls) == 1  # only the first add reached TCGdex


@responses.activate
def test_adding_an_unstored_card_while_tcgdex_is_down_says_so_and_saves_nothing(ash_client):
    responses.get(CARD_URL, status=503)

    html = add(ash_client).content.decode()

    assert "We couldn&#x27;t add this card" in html
    assert "Details unavailable" in html
    assert not Card.objects.exists()
    assert not OwnedCard.objects.exists()


@responses.activate
def test_steps_only_touch_the_requesters_own_rows(ash_client, ash, client):
    responses.get(CARD_URL, json=PIKACHU)
    add(ash_client)
    add(ash_client)
    misty = make_user("misty")
    client.force_login(misty)  # the same test client, now signed in as misty

    before = details(client).content.decode()
    remove(client)
    add(client, "reverse")

    assert "Add to collection" in before and "You own" not in before
    assert OwnedCard.objects.get(user=ash).quantity == 2
    mine = OwnedCard.objects.get(user=misty)
    assert (mine.variant.variant, mine.quantity) == ("reverse", 1)


@pytest.mark.parametrize("action", [add, remove])
def test_tile_actions_require_sign_in(client, db, action):
    response = action(client)

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    assert not OwnedCard.objects.exists()


def test_tile_actions_only_accept_post(ash_client):
    response = ash_client.get(reverse("catalog:tile_add", args=["sv03.5-025"]))

    assert response.status_code == 405
