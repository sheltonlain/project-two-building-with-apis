from datetime import timedelta
from types import SimpleNamespace

import pytest
import requests
import responses
from django.core.cache.backends import base as base_cache
from django.core.cache.backends import db as db_cache
from django.utils import timezone

from catalog import tcgdex

CARDS_URL = f"{tcgdex.BASE_URL}/cards"
PIKACHU = [{"id": "base1-58", "localId": "58", "name": "Pikachu", "image": "https://img/base1/58"}]


@pytest.fixture
def advance_clock(monkeypatch):
    """Move the clocks forward, so cached entries can expire without sleeping.

    The database cache reads expiry with `tz_now` but writes it with `time.time`, and the client
    stamps the outage flag with `timezone.now`, so all three move together. Each call moves them to
    `seconds` after the real time.
    """
    start = timezone.now()

    def advance(seconds):
        later = start + timedelta(seconds=seconds)
        monkeypatch.setattr(db_cache, "tz_now", lambda: later)
        monkeypatch.setattr(base_cache, "time", SimpleNamespace(time=later.timestamp))
        monkeypatch.setattr(tcgdex, "timezone", SimpleNamespace(now=lambda: later))

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


@pytest.mark.django_db
@responses.activate
def test_set_and_rarity_filters_are_exact_and_each_combination_is_cached_separately():
    responses.get(CARDS_URL, json=PIKACHU)

    for _ in range(2):
        tcgdex.search_cards(set_id="sv03")
        tcgdex.search_cards(rarity="Common")
        tcgdex.search_cards(" Pika ", set_id="sv03", rarity="Common")

    assert [call.request.params for call in responses.calls] == [
        {"set.id": "eq:sv03"},
        {"rarity": "eq:Common"},
        {"name": "pika", "set.id": "eq:sv03", "rarity": "eq:Common"},
    ]


SERIES_URL = f"{tcgdex.BASE_URL}/series"


def fake_series():
    """TCGdex lists series and each series' sets oldest first; detail adds releaseDate."""
    details = {
        "base": ("Base", "1999-01-09", [("base1", "Base Set"), ("base2", "Jungle")]),
        "sv": (
            "Scarlet & Violet",
            "2023-03-31",
            [("sv01", "Scarlet & Violet"), ("sv02", "Paldea Evolved")],
        ),
        "swsh": ("Sword & Shield", "2020-02-07", [("swsh1", "Sword & Shield")]),
    }
    responses.get(SERIES_URL, json=[{"id": sid, "name": d[0]} for sid, d in details.items()])
    for sid, (name, released, sets) in details.items():
        responses.get(
            f"{SERIES_URL}/{sid}",
            json={
                "id": sid,
                "name": name,
                "releaseDate": released,
                "sets": [{"id": set_id, "name": set_name} for set_id, set_name in sets],
            },
        )


@pytest.mark.django_db
@responses.activate
def test_set_groups_list_series_newest_first_with_their_sets_newest_first_and_are_cached():
    fake_series()

    groups = tcgdex.set_groups()
    calls_after_first = len(responses.calls)

    assert groups == [
        {
            "name": "Scarlet & Violet",
            "sets": [
                {"id": "sv02", "name": "Paldea Evolved"},
                {"id": "sv01", "name": "Scarlet & Violet"},
            ],
        },
        {"name": "Sword & Shield", "sets": [{"id": "swsh1", "name": "Sword & Shield"}]},
        {
            "name": "Base",
            "sets": [{"id": "base2", "name": "Jungle"}, {"id": "base1", "name": "Base Set"}],
        },
    ]
    assert tcgdex.set_groups() == groups
    assert len(responses.calls) == calls_after_first == 4


RARITIES_URL = f"{tcgdex.BASE_URL}/rarities"


@pytest.mark.django_db
@responses.activate
def test_rarities_are_alphabetical_ignoring_case_and_cached():
    responses.get(RARITIES_URL, json=["Uncommon", "Double rare", "Common", "ACE SPEC Rare"])

    assert tcgdex.rarities() == ["ACE SPEC Rare", "Common", "Double rare", "Uncommon"]
    assert tcgdex.rarities() == ["ACE SPEC Rare", "Common", "Double rare", "Uncommon"]
    assert len(responses.calls) == 1


@pytest.mark.django_db
@responses.activate
@pytest.mark.parametrize(
    ("url", "load"),
    [
        pytest.param(RARITIES_URL, tcgdex.rarities, id="rarities"),
        pytest.param(SERIES_URL, tcgdex.set_groups, id="set-groups"),
    ],
)
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param({"status": 500}, id="http-500"),
        pytest.param({"json": {"error": "surprise"}}, id="wrong-shape"),
    ],
)
def test_option_list_failures_raise_provider_unavailable_and_trip_the_breaker(url, load, failure):
    responses.get(url, **failure)

    with pytest.raises(tcgdex.ProviderUnavailable):
        load()
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")

    assert len(responses.calls) == 1


@pytest.mark.django_db
@responses.activate
def test_a_series_detail_that_fails_makes_the_set_groups_unavailable():
    responses.get(SERIES_URL, json=[{"id": "sv", "name": "Scarlet & Violet"}])
    responses.get(f"{SERIES_URL}/sv", status=404)

    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.set_groups()


@pytest.mark.django_db
@responses.activate
def test_a_user_retry_checks_tcgdex_despite_the_breaker_and_success_closes_it():
    responses.get(CARDS_URL, status=503)
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")
    responses.replace(responses.GET, CARDS_URL, json=PIKACHU)

    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("char")  # an automatic call still fails fast
    assert len(responses.calls) == 1

    assert [c["name"] for c in tcgdex.search_cards("char", probe=True)] == ["Pikachu"]
    assert len(responses.calls) == 2  # the user retry really asked TCGdex
    assert tcgdex.outage_seconds_left() == 0  # and its success closed the breaker for everyone
    assert [c["name"] for c in tcgdex.search_cards("bulba")] == ["Pikachu"]


@pytest.mark.django_db
@responses.activate
def test_a_failed_user_retry_restarts_the_full_breaker_wait(advance_clock):
    responses.get(CARDS_URL, status=503)
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")
    advance_clock(40)

    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika", probe=True)

    assert len(responses.calls) == 2
    advance_clock(40 + 59)  # 59 s after the failed retry: still open
    with pytest.raises(tcgdex.ProviderUnavailable):
        tcgdex.search_cards("pika")
    assert len(responses.calls) == 2
