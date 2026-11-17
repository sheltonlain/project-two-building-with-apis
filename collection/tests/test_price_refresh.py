from datetime import UTC, datetime
from decimal import Decimal

import pytest
import responses
from django.urls import reverse

from catalog import tcgdex
from catalog.models import CardVariant
from catalog.tests.test_card_detail import detail
from collection.tests.helpers import make_owned, make_user

CARDS_URL = f"{tcgdex.BASE_URL}/cards"
OLD = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def stored_price(card_id, variant="normal"):
    row = CardVariant.objects.get(card__tcgdex_id=card_id, variant=variant)
    return row.market_price, row.price_updated


@responses.activate
def test_viewing_a_tile_for_a_stored_card_updates_its_prices_and_as_of_dates(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "normal", price="0.20", updated=OLD)
    make_owned(ash, "sv03.5-025", "Pikachu", "reverse", price="0.50", updated=OLD)
    responses.get(
        f"{CARDS_URL}/sv03.5-025",
        json=detail(
            variants={"normal": True, "reverse": True},
            tcgplayer={
                "updated": "2026-11-15T20:00:00.000Z",
                "normal": {"marketPrice": 0.28},
                "reverse-holofoil": {"marketPrice": 0.7},
            },
        ),
    )

    ash_client.get(reverse("catalog:tile_details", args=["sv03.5-025"]))

    updated = datetime(2026, 11, 15, 20, tzinfo=UTC)
    assert stored_price("sv03.5-025", "normal") == (Decimal("0.28"), updated)
    assert stored_price("sv03.5-025", "reverse") == (Decimal("0.70"), updated)


def refresh(client, step=None, current_url=""):
    data = {} if step is None else {"step": step}
    response = client.post(
        reverse("collection:refresh_prices"),
        data,
        HTTP_HX_REQUEST="true",
        HTTP_HX_CURRENT_URL=current_url,
    )
    assert response.status_code == 200
    return response.content.decode()


def fake_price(card_id, price):
    responses.get(
        f"{CARDS_URL}/{card_id}",
        json=detail(card_id, tcgplayer={"normal": {"marketPrice": price}}),
    )


@responses.activate
def test_refresh_goes_card_by_card_with_progress_and_ends_with_the_new_total(ash_client, ash):
    make_owned(ash, "sv03.5-001", "Bulbasaur", price="1.00", updated=OLD, quantity=2)
    make_owned(ash, "sv03.5-004", "Charmander", price="1.00", updated=OLD)
    make_owned(ash, "sv03.5-007", "Squirtle", price="1.00", updated=OLD)
    fake_price("sv03.5-001", 2.0)
    fake_price("sv03.5-004", 3.0)
    fake_price("sv03.5-007", 4.0)

    assert "Refreshing 1 of 3…" in refresh(ash_client)  # the button starts it; no fetch yet
    assert stored_price("sv03.5-001")[0] == Decimal("1.00")

    assert "Refreshing 2 of 3…" in refresh(ash_client, 0)
    assert stored_price("sv03.5-001")[0] == Decimal("2.00")
    assert stored_price("sv03.5-004")[0] == Decimal("1.00")  # not reached yet

    assert "Refreshing 3 of 3…" in refresh(ash_client, 1)
    done = refresh(ash_client, 2)

    assert "Refreshing" not in done
    assert "Refreshed prices for 3 cards." in done
    assert "$11.00" in done  # 2 × 2.00 + 3.00 + 4.00, in the swapped-in value summary
    assert len(responses.calls) == 3  # one detail call per card


@responses.activate
def test_an_outage_mid_refresh_stops_it_says_so_and_keeps_the_remaining_prices(ash_client, ash):
    make_owned(ash, "sv03.5-001", "Bulbasaur", price="1.00", updated=OLD)
    make_owned(ash, "sv03.5-004", "Charmander", price="1.00", updated=OLD)
    make_owned(ash, "sv03.5-007", "Squirtle", price="1.00", updated=OLD)
    fake_price("sv03.5-001", 2.0)
    responses.get(f"{CARDS_URL}/sv03.5-004", status=503, body="no available server")
    ash_client.raise_request_exception = False  # an unhandled outage shows up as a 500

    refresh(ash_client, 0)
    failed = refresh(ash_client, 1)

    assert "Refreshing" not in failed  # stopped: no further step is requested
    assert 'hx-trigger="load"' not in failed
    assert "TCGdex, the card database, isn't responding" in failed
    assert "Refreshed 1 of 3 cards" in failed
    assert stored_price("sv03.5-001")[0] == Decimal("2.00")  # refreshed before the outage
    assert stored_price("sv03.5-004") == (Decimal("1.00"), OLD)  # kept
    assert stored_price("sv03.5-007") == (Decimal("1.00"), OLD)  # never tried
    assert len(responses.calls) == 2


@responses.activate
def test_when_tcgplayer_has_no_date_the_as_of_date_is_when_the_card_was_fetched(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", price="0.20", updated=OLD)
    responses.get(
        f"{CARDS_URL}/sv03.5-025", json=detail(tcgplayer={"normal": {"marketPrice": 0.28}})
    )
    tile = reverse("catalog:tile_details", args=["sv03.5-025"])

    ash_client.get(tile)
    price, fetched = stored_price("sv03.5-025")
    ash_client.get(tile)  # served from the 24-hour cache

    assert price == Decimal("0.28")
    assert fetched > OLD
    assert stored_price("sv03.5-025")[1] == fetched  # not moved to "now" by the cached copy
    assert len(responses.calls) == 1


@responses.activate
def test_viewing_a_tile_for_an_unsaved_card_stores_nothing(ash_client):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail())

    ash_client.get(reverse("catalog:tile_details", args=["sv03.5-025"]))

    assert not CardVariant.objects.exists()


@responses.activate
def test_refresh_skips_the_card_cache(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", price="0.20", updated=OLD)
    responses.get(
        f"{CARDS_URL}/sv03.5-025", json=detail(tcgplayer={"normal": {"marketPrice": 0.28}})
    )
    ash_client.get(reverse("catalog:tile_details", args=["sv03.5-025"]))  # now cached
    responses.replace(
        responses.GET,
        f"{CARDS_URL}/sv03.5-025",
        json=detail(tcgplayer={"normal": {"marketPrice": 0.35}}),
    )

    refresh(ash_client, 0)

    assert stored_price("sv03.5-025")[0] == Decimal("0.35")


@responses.activate
def test_refresh_swaps_in_the_shown_entries_with_their_new_prices(ash_client, ash):
    owned = make_owned(ash, "sv03.5-025", "Pikachu", price="0.20", updated=OLD, quantity=2)
    fake_price("sv03.5-025", 0.35)

    done = refresh(ash_client, 0, current_url="http://testserver/collection/?sort=name")

    assert f'id="entry-{owned.pk}"' in done
    assert 'hx-swap-oob="true"' in done
    assert "$0.35" in done
    assert "$0.70" in done  # 2 × 0.35


@responses.activate
def test_a_card_tcgdex_no_longer_has_is_skipped(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", price="0.20", updated=OLD)
    responses.get(f"{CARDS_URL}/sv03.5-025", status=404)

    done = refresh(ash_client, 0)

    assert "Refreshed prices for 1 card." in done
    assert stored_price("sv03.5-025") == (Decimal("0.20"), OLD)


def test_the_collection_page_has_a_refresh_prices_button(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", price="0.20")

    html = ash_client.get(reverse("collection:index")).content.decode()

    assert "Refresh prices" in html
    assert reverse("collection:refresh_prices") in html


def test_refresh_requires_sign_in_and_post(client, ash):
    url = reverse("collection:refresh_prices")

    assert client.post(url)["Location"].startswith(reverse("login"))
    client.force_login(ash)
    assert client.get(url).status_code == 405


def test_refresh_with_an_empty_collection_finishes_at_once(ash_client):
    assert "Refreshed prices for 0 cards." in refresh(ash_client)
