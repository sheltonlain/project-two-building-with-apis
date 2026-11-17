"""Collection entries and wishes link their image and name to the card's page."""

import re

import pytest
from django.urls import reverse

from collection.tests.helpers import make_owned, make_user, make_wish


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def card_links(html, card_id):
    """Each <a>…</a> pointing at the card's page, in full."""
    card_url = re.escape(reverse("catalog:card_detail", args=[card_id]))
    return re.findall(rf'<a href="{card_url}"[^>]*>.*?</a>', html, re.DOTALL)


def assert_image_and_name_link_to_the_card(html, card_id, name):
    links = card_links(html, card_id)
    assert len(links) == 2  # the image and the name
    assert any("<img" in link for link in links)
    assert any(re.search(rf">\s*{name}\s*</a>$", link) for link in links)
    # Buttons and notes controls stay outside the links, so they work in place.
    assert not any("<button" in link or "<form" in link for link in links)


def test_a_collection_entry_links_its_image_and_name_to_the_card_page(ash_client, ash):
    make_owned(ash, "sv03.5-006", "Charizard", "holo", price="9.00")

    html = ash_client.get(reverse("collection:index")).content.decode()

    assert_image_and_name_link_to_the_card(html, "sv03.5-006", "Charizard")


def test_a_wish_links_its_image_and_name_to_the_card_page(ash_client, ash):
    make_wish(ash, "sv03.5-025", "Pikachu", price="1.00")

    html = ash_client.get(reverse("collection:wishlist")).content.decode()

    assert_image_and_name_link_to_the_card(html, "sv03.5-025", "Pikachu")


HTMX = {"HTTP_HX_REQUEST": "true"}


def test_an_entry_swapped_in_by_plus_keeps_its_links(ash_client, ash):
    entry = make_owned(ash, "sv03.5-006", "Charizard", "holo", price="9.00")

    response = ash_client.post(reverse("collection:entry_add", args=[entry.pk]), **HTMX)

    assert_image_and_name_link_to_the_card(response.content.decode(), "sv03.5-006", "Charizard")


def test_the_wishlist_body_swapped_in_by_got_it_keeps_the_other_wishes_links(ash_client, ash):
    make_wish(ash, "sv03.5-025", "Pikachu", price="1.00")
    got = make_wish(ash, "sv03.5-006", "Charizard", price="9.00")

    response = ash_client.post(reverse("collection:wish_got_it", args=[got.pk]), **HTMX)

    assert_image_and_name_link_to_the_card(response.content.decode(), "sv03.5-025", "Pikachu")
