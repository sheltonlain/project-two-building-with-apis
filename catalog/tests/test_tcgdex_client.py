from datetime import timedelta

import pytest
import requests
import responses
from django.core.cache.backends import db as db_cache
from django.utils import timezone

from catalog import tcgdex

CARDS_URL = f"{tcgdex.BASE_URL}/cards"
PIKACHU = [{"id": "base1-58", "localId": "58", "name": "Pikachu", "image": "https://img/base1/58"}]


@pytest.fixture
def advance_clock(monkeypatch):
    """Move the database cache's clock forward, so cached entries can expire without sleeping."""

    def advance(seconds):
        later = timezone.now() + timedelta(seconds=seconds)
        monkeypatch.setattr(db_cache, "tz_now", lambda: later)

    return advance


@pytest.mark.django_db
@responses.activate
def test_one_failure_trips_the_breaker_until_it_expires(advance_clock):
    responses.get(CARDS_URL, body=requests.ConnectTimeout("too slow"))

    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("char")

    assert len(responses.calls) == 1  # the second call failed fast, without a request

    advance_clock(61)
    responses.replace(responses.GET, CARDS_URL, json=PIKACHU)

    assert [card["name"] for card in tcgdex.search_cards("char")] == ["Pikachu"]
    assert len(responses.calls) == 2


@pytest.mark.django_db
@responses.activate
def test_breaker_is_still_set_just_before_sixty_seconds(advance_clock):
    responses.get(CARDS_URL, status=500)
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")

    advance_clock(59)

    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")
    assert len(responses.calls) == 1


@pytest.mark.django_db
@responses.activate
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param({"body": requests.ConnectTimeout("connect")}, id="connect-timeout"),
        pytest.param({"body": requests.ReadTimeout("read")}, id="read-timeout"),
        pytest.param({"body": requests.ConnectionError("refused")}, id="connection-error"),
        pytest.param({"status": 500}, id="http-500"),
        pytest.param({"status": 503, "body": "no available server"}, id="http-503"),
        pytest.param({"body": "<html>not json</html>"}, id="invalid-json"),
        pytest.param({"json": {"error": "surprise"}}, id="not-a-list"),
        pytest.param({"json": [{"localId": "1"}]}, id="card-missing-fields"),
    ],
)
def test_every_kind_of_failure_raises_provider_unavailable_and_trips_the_breaker(failure):
    responses.get(CARDS_URL, **failure)

    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")

    assert len(responses.calls) == 1


@pytest.mark.django_db
@responses.activate
def test_requests_use_a_3s_connect_and_5s_read_timeout():
    responses.get(CARDS_URL, json=PIKACHU)

    tcgdex.search_cards("pika")

    assert responses.calls[0].request.req_kwargs["timeout"] == (3, 5)


@pytest.mark.django_db
@responses.activate
def test_a_404_search_means_no_matches_and_does_not_trip_the_breaker():
    responses.get(CARDS_URL, status=404)

    assert tcgdex.search_cards("zzzz") == []

    responses.replace(responses.GET, CARDS_URL, json=PIKACHU)
    assert len(tcgdex.search_cards("pika")) == 1


@pytest.mark.django_db
@responses.activate
def test_search_sends_a_lowercased_name_and_shares_the_cache_across_case_and_spaces():
    responses.get(CARDS_URL, json=PIKACHU)

    tcgdex.search_cards("  PIKA ")
    tcgdex.search_cards("pika")

    assert len(responses.calls) == 1
    assert responses.calls[0].request.params == {"name": "pika"}


@pytest.mark.django_db
@responses.activate
def test_search_results_carry_the_low_quality_webp_tile_image():
    responses.get(CARDS_URL, json=PIKACHU + [{"id": "x-1", "localId": "1", "name": "Pikachu"}])

    cards = tcgdex.search_cards("pika")

    assert cards == [
        {
            "id": "base1-58",
            "local_id": "58",
            "name": "Pikachu",
            "tile_image": "https://img/base1/58/low.webp",
        },
        {"id": "x-1", "local_id": "1", "name": "Pikachu", "tile_image": None},
    ]
