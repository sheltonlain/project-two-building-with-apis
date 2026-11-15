"""The only code in the app that talks to TCGdex (https://tcgdex.dev).

Every request has a 3 s connect / 5 s read timeout and is never retried. Failures are raised as
this module's own exceptions, which views turn into user-facing messages.
"""

import hashlib
from urllib.parse import urlencode

import requests
from django.core.cache import cache

BASE_URL = "https://api.tcgdex.net/v2/en"
TIMEOUT = (3, 5)  # (connect, read) seconds
OUTAGE_KEY = "tcgdex:down"
OUTAGE_SECONDS = 60
SEARCH_CACHE_SECONDS = 24 * 60 * 60


class TCGdexError(Exception):
    """Base class for every error this client raises."""


class ProviderUnavailable(TCGdexError):
    """TCGdex timed out, could not be reached, failed, or sent something unusable."""


class NotFound(TCGdexError):
    """TCGdex has no such resource."""


def _fetch(path, parse, params=None):
    """GET a TCGdex path and return `parse(json)`.

    Any failure (timeout, connection error, server error, malformed or unexpectedly shaped
    response) sets the outage flag for OUTAGE_SECONDS. While it is set, calls raise
    ProviderUnavailable at once without making a request.
    """
    if cache.get(OUTAGE_KEY):
        raise ProviderUnavailable("TCGdex was recently unavailable")
    try:
        data = _request_json(path, params)
        try:
            return parse(data)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderUnavailable(f"Unexpected response shape from {path}") from exc
    except ProviderUnavailable:
        cache.set(OUTAGE_KEY, True, OUTAGE_SECONDS)
        raise


def _request_json(path, params):
    try:
        response = requests.get(f"{BASE_URL}/{path}", params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ProviderUnavailable(str(exc)) from exc

    if response.status_code == 404:
        raise NotFound(path)
    if not response.ok:
        raise ProviderUnavailable(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderUnavailable("Malformed JSON") from exc


def search_cards(name):
    """Return every card whose name contains `name` (any case).

    Each result is a dict with id, local_id, name and tile_image. The full list for each distinct
    filter combination is fetched once and cached for 24 hours; callers paginate it themselves.
    """
    params = {"name": name.strip().lower()}
    key = "tcgdex:search:" + hashlib.sha256(urlencode(sorted(params.items())).encode()).hexdigest()
    cards = cache.get(key)
    if cards is None:
        try:
            cards = _fetch("cards", _brief_cards, params=params)
        except NotFound:
            cards = []
        cache.set(key, cards, SEARCH_CACHE_SECONDS)
    return cards


def _brief_cards(data):
    if not isinstance(data, list):
        raise TypeError("expected a list of cards")
    return [
        {
            "id": card["id"],
            "local_id": card.get("localId") or "",
            "name": card["name"],
            "tile_image": image_url(card.get("image"), "low"),
        }
        for card in data
    ]


def image_url(base, quality="high"):
    """TCGdex image URLs have no suffix; add the quality ("low" or "high") and webp extension."""
    return f"{base}/{quality}.webp" if base else None
