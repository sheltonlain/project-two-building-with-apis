import re

import pytest
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalog import tcgdex

CARDS_URL = f"{tcgdex.BASE_URL}/cards"
SEARCH_URL = reverse("catalog:search")


def fake_cards(count):
    return [
        {
            "id": f"set1-{n}",
            "localId": str(n),
            "name": f"Pikachu {n}",
            "image": f"https://assets.tcgdex.net/en/set/set1/{n}",
        }
        for n in range(1, count + 1)
    ]


@pytest.fixture
def signed_in_client(client, db):
    user = get_user_model().objects.create_user(
        username="ash", email="ash@example.com", password="x"
    )
    client.force_login(user)
    return client


def tile_names(response):
    return [card["name"] for card in response.context["page"].object_list]


@responses.activate
def test_search_ids_are_fetched_once_then_paginated_from_the_cache(signed_in_client):
    responses.get(CARDS_URL, json=fake_cards(50))

    first = signed_in_client.get(SEARCH_URL, {"name": "pika"})
    last = signed_in_client.get(SEARCH_URL, {"name": "pika", "page": 3})
    repeat = signed_in_client.get(SEARCH_URL, {"name": "pika"})

    assert "50 cards found" in first.content.decode()
    assert tile_names(first) == [f"Pikachu {n}" for n in range(1, 25)]
    assert tile_names(last) == ["Pikachu 49", "Pikachu 50"]
    assert tile_names(repeat) == tile_names(first)
    assert len(responses.calls) == 1


@responses.activate
@pytest.mark.parametrize("name", ["", "   "])
def test_empty_search_asks_for_a_filter_and_makes_no_tcgdex_call(signed_in_client, name):
    responses.get(CARDS_URL, json=fake_cards(3))

    response = signed_in_client.get(SEARCH_URL, {"name": name})

    assert response.status_code == 200
    assert "Pick a name, set or rarity to start." in response.content.decode()
    assert len(responses.calls) == 0


def test_search_requires_sign_in(client, db):
    response = client.get(SEARCH_URL, {"name": "pika"})

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@responses.activate
def test_first_visit_shows_an_intro_and_makes_no_call(signed_in_client):
    response = signed_in_client.get(SEARCH_URL)

    content = response.content.decode()
    assert "Pick a name, set or rarity to start." not in content
    assert 'name="name"' in content
    assert len(responses.calls) == 0


@responses.activate
def test_failed_search_shows_unavailable_message_with_a_retry_of_the_same_query(
    signed_in_client,
):
    responses.get(CARDS_URL, status=503)

    response = signed_in_client.get(SEARCH_URL, {"name": "pika", "page": "2"})

    content = response.content.decode()
    assert response.status_code == 200
    assert "We couldn't reach TCGdex" in content
    assert "not a problem on your end" not in content
    assert 'href="?name=pika&amp;page=2"' in content
    assert ">Retry</a>" in content


@responses.activate
def test_tiles_show_name_and_low_quality_webp_image(signed_in_client):
    responses.get(CARDS_URL, json=fake_cards(2))

    content = signed_in_client.get(SEARCH_URL, {"name": "pika"}).content.decode()

    assert 'src="https://assets.tcgdex.net/en/set/set1/1/low.webp"' in content
    assert "Pikachu 2" in content
    assert "2 cards found" in content


@responses.activate
def test_numbered_page_links_keep_the_search(signed_in_client):
    responses.get(CARDS_URL, json=fake_cards(50))

    response = signed_in_client.get(SEARCH_URL, {"name": "pika"})

    content = response.content.decode()
    assert 'href="?name=pika&amp;page=2"' in content
    assert 'href="?name=pika&amp;page=3"' in content
    assert 'aria-current="page">1<' in content


@responses.activate
def test_no_matches_says_so(signed_in_client):
    responses.get(CARDS_URL, json=[])

    content = signed_in_client.get(SEARCH_URL, {"name": "zzzz"}).content.decode()

    assert "0 cards found" in content
    assert "No cards match that name." in content


@responses.activate
def test_htmx_request_gets_only_the_results_fragment(signed_in_client):
    responses.get(CARDS_URL, json=fake_cards(2))

    partial = signed_in_client.get(SEARCH_URL, {"name": "pika"}, headers={"HX-Request": "true"})
    restore = signed_in_client.get(
        SEARCH_URL,
        {"name": "pika"},
        headers={"HX-Request": "true", "HX-History-Restore-Request": "true"},
    )

    assert partial.content.decode().lstrip().startswith('<div id="search-panel">')
    assert "<html" in restore.content.decode()


@responses.activate
def test_search_page_has_a_loading_indicator(signed_in_client):
    content = signed_in_client.get(SEARCH_URL).content.decode()

    assert 'hx-indicator="#search-indicator"' in content
    assert 'id="search-indicator" class="htmx-indicator' in content


@responses.activate
def test_htmx_results_carry_the_current_search_in_the_name_box(signed_in_client):
    """The name box is part of each swapped response, so Back restores the right search."""
    responses.get(CARDS_URL, json=fake_cards(2))

    partial = signed_in_client.get(SEARCH_URL, {"name": "pika"}, headers={"HX-Request": "true"})

    assert 'name="name" value="pika"' in partial.content.decode()


PLACEHOLDER = "/static/images/placeholder_image.jfif"


def placeholder_is_hidden(tile):
    tag = re.search(r"<div class=\"card-image-placeholder[^>]*>", tile).group(0)
    return re.search(r"\shidden(\s|>)", tag) is not None


def tile_html(content, card_id):
    start = content.index(f'data-card-id="{card_id}"')
    return content[start : content.index("</li>", start)]


@responses.activate
def test_card_without_an_image_shows_the_placeholder_with_name_and_number(signed_in_client):
    responses.get(CARDS_URL, json=[{"id": "x-7", "localId": "7", "name": "Mystery Card"}])

    tile = tile_html(signed_in_client.get(SEARCH_URL, {"name": "myst"}).content.decode(), "x-7")

    assert PLACEHOLDER in tile
    assert "Mystery Card" in tile
    assert "#7" in tile
    assert "low.webp" not in tile
    assert not placeholder_is_hidden(tile)


@responses.activate
def test_card_image_falls_back_to_the_placeholder_when_it_fails_to_load(signed_in_client):
    responses.get(CARDS_URL, json=fake_cards(1))

    tile = tile_html(signed_in_client.get(SEARCH_URL, {"name": "pika"}).content.decode(), "set1-1")

    assert 'src="https://assets.tcgdex.net/en/set/set1/1/low.webp"' in tile
    assert "onerror=" in tile
    assert PLACEHOLDER in tile
    assert placeholder_is_hidden(tile)
