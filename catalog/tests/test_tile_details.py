import re

import pytest
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalog import tcgdex
from catalog.tests.test_card_detail import detail

CARDS_URL = f"{tcgdex.BASE_URL}/cards"


def tile_url(card_id):
    return reverse("catalog:tile_details", args=[card_id])


@pytest.fixture
def signed_in_client(client, db):
    user = get_user_model().objects.create_user(
        username="ash", email="ash@example.com", password="x"
    )
    client.force_login(user)
    return client


@responses.activate
def test_a_failing_tile_shows_its_own_retry_while_other_tiles_still_load(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail("sv03.5-025"))
    responses.get(f"{CARDS_URL}/sv03.5-004", status=503, body="no available server")
    signed_in_client.get(tile_url("sv03.5-025"))  # this tile loaded before the failure

    failed = signed_in_client.get(tile_url("sv03.5-004"), {"variant": "reverse"})
    other = signed_in_client.get(tile_url("sv03.5-025"))

    failed_html = failed.content.decode()
    assert failed.status_code == 200  # HTMX only swaps in successful responses
    assert "<html" not in failed_html  # a tile-sized fragment, not a page
    assert "Details unavailable" in failed_html
    assert "data-tile-failed" in failed_html  # counted by the banner above the grid
    retry_url = f"{tile_url('sv03.5-004')}?variant=reverse"
    assert f'hx-get="{retry_url}"' in failed_html  # retries this tile, keeping its variant
    # Retries by itself once the 60 s breaker closes (plus up to 3 s of spread), or on demand.
    delay = re.search(r'hx-trigger="load delay:(\d+)s, retry"', failed_html)
    assert delay and 60 <= int(delay.group(1)) <= 63

    other_html = other.content.decode()
    assert "Details unavailable" not in other_html
    assert "151 · Common" in other_html


TWO_VARIANT_PRICES = {
    "unit": "USD",
    "normal": {"marketPrice": 0.28},
    "reverse-holofoil": {"marketPrice": 0.7},
}


@responses.activate
def test_tile_shows_set_rarity_variants_and_the_first_variants_price(signed_in_client):
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(variants={"normal": True, "reverse": True}, tcgplayer=TWO_VARIANT_PRICES),
    )

    html = signed_in_client.get(tile_url("sv03.5-025")).content.decode()

    assert "151 · Common" in html
    assert '<option value="normal" selected>Normal</option>' in html
    assert '<option value="reverse">Reverse holo</option>' in html
    assert "$0.28" in html
    assert f'hx-get="{tile_url("sv03.5-025")}" hx-trigger="change"' in html  # switching reloads


@responses.activate
def test_choosing_a_variant_shows_that_variants_price(signed_in_client):
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(variants={"normal": True, "reverse": True}, tcgplayer=TWO_VARIANT_PRICES),
    )

    html = signed_in_client.get(tile_url("sv03.5-025"), {"variant": "reverse"}).content.decode()

    assert '<option value="reverse" selected>Reverse holo</option>' in html
    assert "$0.70" in html
    assert "$0.28" not in html


@responses.activate
def test_an_unknown_variant_falls_back_to_the_first_one(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail(tcgplayer=TWO_VARIANT_PRICES))

    html = signed_in_client.get(tile_url("sv03.5-025"), {"variant": "holo"}).content.decode()

    assert '<option value="normal" selected>Normal</option>' in html


@responses.activate
def test_a_single_variant_card_is_preselected_and_fixed(signed_in_client):
    responses.get(f"{CARDS_URL}/base1-4", json=detail("base1-4", variants={"holo": True}))

    html = signed_in_client.get(tile_url("base1-4")).content.decode()

    select = re.search(r"<select[^>]*>", html).group(0)
    assert "disabled" in select
    assert "hx-get" not in select
    assert html.count("<option") == 1
    assert '<option value="holo" selected>Holo</option>' in html


@responses.activate
def test_a_variant_without_a_price_says_no_price(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail())

    html = signed_in_client.get(tile_url("sv03.5-025")).content.decode()

    assert "No price" in html
    assert "$" not in html


@responses.activate
def test_card_details_are_cached(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail())

    signed_in_client.get(tile_url("sv03.5-025"))
    signed_in_client.get(tile_url("sv03.5-025"), {"variant": "normal"})

    assert len(responses.calls) == 1


@responses.activate
def test_an_unknown_card_says_so_without_tripping_the_breaker(signed_in_client):
    responses.get(f"{CARDS_URL}/nope-1", status=404)

    html = signed_in_client.get(tile_url("nope-1")).content.decode()

    assert "no longer lists this card" in html
    assert "data-tile-failed" not in html
    assert tcgdex.outage_seconds_left() == 0


@responses.activate
def test_while_the_breaker_is_open_tiles_fail_fast_and_wait_for_it(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-004", status=500)
    signed_in_client.get(tile_url("sv03.5-004"))

    html = signed_in_client.get(tile_url("sv03.5-025")).content.decode()

    assert len(responses.calls) == 1  # the second tile made no request
    assert "Details unavailable" in html
    assert re.search(r'hx-trigger="load delay:(6[0-3]|59)s, retry"', html)


def test_tile_details_require_sign_in(client, db):
    response = client.get(tile_url("sv03.5-025"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@responses.activate
def test_try_now_reaches_tcgdex_while_the_breaker_is_open_and_tells_the_page(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-004", status=500)
    failed = signed_in_client.get(tile_url("sv03.5-004")).content.decode()
    responses.replace(responses.GET, f"{CARDS_URL}/sv03.5-004", json=detail("sv03.5-004"))

    automatic = signed_in_client.get(tile_url("sv03.5-004"))
    retried = signed_in_client.get(tile_url("sv03.5-004"), HTTP_X_USER_RETRY="1")

    try_now = re.search(r"<button[^>]*data-try-now[^>]*>", failed).group(0)
    assert f'hx-get="{tile_url("sv03.5-004")}"' in try_now
    assert """hx-headers='{"X-User-Retry": "1"}'""" in try_now
    assert "Details unavailable" in automatic.content.decode()  # failed fast, no request
    assert "HX-Trigger" not in automatic.headers
    assert "151 · Common" in retried.content.decode()
    assert retried.headers["HX-Trigger"] == "tcgdex-back"  # so the page retries other tiles
    assert len(responses.calls) == 2
