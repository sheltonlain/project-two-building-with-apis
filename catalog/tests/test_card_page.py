import re
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalog import tcgdex
from catalog.models import CardVariant
from catalog.tests.test_card_detail import detail
from collection.tests.helpers import make_owned, make_user, make_variant

CARDS_URL = f"{tcgdex.BASE_URL}/cards"


def page_url(card_id):
    return reverse("catalog:card_detail", args=[card_id])


@pytest.fixture
def signed_in_client(client, db):
    user = get_user_model().objects.create_user(
        username="ash", email="ash@example.com", password="x"
    )
    client.force_login(user)
    return client


@responses.activate
def test_the_page_shows_the_card_and_every_variants_price_and_date(signed_in_client):
    prices = {
        "updated": "2026-11-10T20:05:12.000Z",
        "unit": "USD",
        "normal": {"marketPrice": 0.28},
        "reverse-holofoil": {"marketPrice": 0.7},
    }
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(variants={"normal": True, "reverse": True}, tcgplayer=prices),
    )

    response = signed_in_client.get(page_url("sv03.5-025"))

    html = response.content.decode()
    assert response.status_code == 200
    assert "<h1" in html and "Pikachu" in html
    assert "#025" in html
    assert "151" in html
    assert "Common" in html
    assert "https://assets.tcgdex.net/en/sv/sv03.5/025/high.webp" in html  # the large image
    assert "Normal" in html and "$0.28" in html
    assert "Reverse holo" in html and "$0.70" in html
    assert html.count("as of Nov 10, 2026") == 2  # each variant's price date


@responses.activate
def test_a_stored_card_is_shown_from_the_database_when_tcgdex_is_down(signed_in_client):
    make_variant("sv03.5-025", "Pikachu", "normal", "0.28", datetime(2026, 11, 3, tzinfo=UTC))
    make_variant("sv03.5-025", "Pikachu", "reverse", "0.70", datetime(2026, 11, 3, tzinfo=UTC))
    responses.get(f"{CARDS_URL}/sv03.5-025", status=503)

    response = signed_in_client.get(page_url("sv03.5-025"))

    html = response.content.decode()
    assert response.status_code == 200
    assert "<h1" in html and "Pikachu" in html
    assert "#025" in html and "151" in html and "Common" in html
    assert "Normal" in html and "$0.28" in html
    assert "Reverse holo" in html and "$0.70" in html
    assert html.count("as of Nov 3, 2026") == 2  # the stored price dates
    assert "prices may be out of date" in html


@responses.activate
def test_an_unknown_card_gets_a_friendly_not_found_page(signed_in_client):
    responses.get(f"{CARDS_URL}/nope-1", status=404)

    response = signed_in_client.get(page_url("nope-1"))

    html = response.content.decode()
    assert response.status_code == 404
    assert "We couldn't find that card" in html
    assert f'href="{reverse("catalog:search")}"' in html  # a way back to searching
    assert tcgdex.outage_seconds_left() == 0  # not treated as an outage


@responses.activate
def test_an_unstored_card_shows_a_friendly_message_and_retries_itself(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", status=503)

    response = signed_in_client.get(page_url("sv03.5-025"))

    html = response.content.decode()
    assert response.status_code == 200
    assert "TCGdex, the card database, didn't respond" in html
    # Retries by itself once the 60 s breaker closes (plus up to 3 s of spread)...
    delay = re.search(r'hx-trigger="load delay:(\d+)s"', html)
    assert delay and 60 <= int(delay.group(1)) <= 63
    assert f'data-retry-countdown="{delay.group(1)}"' in html
    auto = re.search(r"<div hidden[^>]*>", html).group(0)
    assert f'hx-get="{page_url("sv03.5-025")}"' in auto
    assert "X-User-Retry" not in auto  # never probes an open breaker
    # ...and Retry is a user retry.
    retry = re.search(r"<button[^>]*>Retry</button>", html).group(0)
    assert """hx-headers='{"X-User-Retry": "1"}'""" in retry


@responses.activate
def test_retry_reaches_tcgdex_while_the_breaker_is_open_and_swaps_in_the_card(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", status=503)
    signed_in_client.get(page_url("sv03.5-025"))
    responses.replace(responses.GET, f"{CARDS_URL}/sv03.5-025", json=detail())

    automatic = signed_in_client.get(page_url("sv03.5-025"), HTTP_HX_REQUEST="true")
    retried = signed_in_client.get(
        page_url("sv03.5-025"), HTTP_HX_REQUEST="true", HTTP_X_USER_RETRY="1"
    )

    assert len(responses.calls) == 2  # the automatic retry failed fast, without a request
    assert "didn't respond" in automatic.content.decode()
    html = retried.content.decode()
    assert "<html" not in html  # just the page body, swapped in place
    assert 'id="card-page"' in html and "Pikachu" in html


@responses.activate
def test_opening_the_page_refreshes_the_stored_cards_prices(signed_in_client):
    make_variant("sv03.5-025", "Pikachu", "normal", "0.10")
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(tcgplayer={"unit": "USD", "normal": {"marketPrice": 0.28}}),
    )

    signed_in_client.get(page_url("sv03.5-025"))

    stored = CardVariant.objects.get(card__tcgdex_id="sv03.5-025", variant="normal")
    assert stored.market_price == Decimal("0.28")


@responses.activate
def test_card_details_are_cached(signed_in_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail())

    signed_in_client.get(page_url("sv03.5-025"))
    signed_in_client.get(page_url("sv03.5-025"))

    assert len(responses.calls) == 1


def test_the_page_requires_sign_in(client, db):
    response = client.get(page_url("sv03.5-025"))

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={page_url('sv03.5-025')}"


@responses.activate
def test_owned_variants_show_the_count_total_value_and_note(signed_in_client):
    prices = {"normal": {"marketPrice": 0.28}, "reverse-holofoil": {"marketPrice": 0.7}}
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(variants={"normal": True, "reverse": True}, tcgplayer=prices),
    )
    ash = get_user_model().objects.get(username="ash")
    entry = make_owned(ash, "sv03.5-025", "Pikachu", "reverse", "0.70", quantity=3)
    entry.notes = "From my first booster"
    entry.save()
    make_owned(make_user("misty"), "sv03.5-025", "Pikachu", "normal", "0.28", quantity=9)

    response = signed_in_client.get(page_url("sv03.5-025"))

    variants = {v["code"]: v for v in response.context["variants"]}
    assert variants["reverse"]["entry"].quantity == 3
    assert variants["normal"]["entry"] is None  # misty's copies aren't ash's
    html = response.content.decode()
    assert "3 owned" in html
    assert 'Total Value: <span class="font-semibold">$2.10</span>' in html  # at today's price
    assert "From my first booster" in html
    assert "9 owned" not in html
    assert "Not in your collection" in html  # the Normal variant
