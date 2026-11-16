"""The only code in the app that talks to TCGdex (https://tcgdex.dev).

Every request has a 3 s connect / 5 s read timeout and is never retried. Failures are raised as
this module's own exceptions, which views turn into user-facing messages.
"""

import hashlib
import math
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from urllib.parse import quote, urlencode

import requests
from django.core.cache import cache
from django.utils import timezone

BASE_URL = "https://api.tcgdex.net/v2/en"
TIMEOUT = (3, 5)  # (connect, read) seconds
OUTAGE_KEY = "tcgdex:down"
OUTAGE_SECONDS = 60
SEARCH_CACHE_SECONDS = 24 * 60 * 60
OPTIONS_CACHE_SECONDS = 24 * 60 * 60
CARD_CACHE_SECONDS = 24 * 60 * 60

# (TCGdex variant flag, the app's variant code, display label, TCGplayer price keys to try in
# order), in display order. Older sets use "unlimited"/"1st-edition" keys instead of "normal".
VARIANTS = (
    ("normal", "normal", "Normal", ("normal", "unlimited")),
    ("reverse", "reverse", "Reverse holo", ("reverse-holofoil",)),
    ("holo", "holo", "Holo", ("holofoil", "unlimited-holofoil")),
    ("firstEdition", "first_edition", "1st Edition", ("1st-edition-holofoil", "1st-edition")),
    ("wPromo", "w_promo", "W Promo", ()),
)
CENTS = Decimal("0.01")
SERIES_FETCH_WORKERS = 8
SET_GROUPS_KEY = "tcgdex:set-groups"
RARITIES_KEY = "tcgdex:rarities"


class TCGdexError(Exception):
    """Base class for every error this client raises."""


class ProviderUnavailable(TCGdexError):
    """TCGdex timed out, could not be reached, failed, or sent something unusable."""


class NotFound(TCGdexError):
    """TCGdex has no such resource."""


def _fetch(path, parse, params=None, probe=False):
    """GET a TCGdex path and return `parse(json)`, behind the circuit breaker."""
    return _guarded(lambda: parse(_request_json(path, params)), probe)


def _guarded(work, probe=False):
    """Run `work` (which makes TCGdex requests) behind the circuit breaker.

    Any failure (timeout, connection error, server error, malformed or unexpectedly shaped
    response) sets the outage flag for OUTAGE_SECONDS. While it is set, calls raise
    ProviderUnavailable at once without making a request.

    A `probe` is a retry the user asked for: it tries TCGdex even while the flag is set. If it
    succeeds, the flag is cleared for everyone; if it fails, the flag's wait starts again.
    """
    if not probe and cache.get(OUTAGE_KEY):
        raise ProviderUnavailable("TCGdex was recently unavailable")
    try:
        try:
            result = work()
            if probe:
                cache.delete(OUTAGE_KEY)
            return result
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderUnavailable("Unexpected response shape from TCGdex") from exc
    except ProviderUnavailable:
        # The value is when the flag expires, so pages can say when TCGdex will be tried again.
        expires = timezone.now().timestamp() + OUTAGE_SECONDS
        cache.set(OUTAGE_KEY, expires, OUTAGE_SECONDS)
        raise


def outage_seconds_left():
    """Seconds until the outage flag expires and TCGdex is tried again; 0 when it isn't set."""
    expires = cache.get(OUTAGE_KEY)
    if not isinstance(expires, int | float):
        return 0
    return max(0, math.ceil(expires - timezone.now().timestamp()))


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


def search_cards(name="", set_id="", rarity="", probe=False):
    """Return every card matching the given filters; empty filters are left out.

    The name is a contains match (any case). Set and rarity are sent with TCGdex's `eq:` prefix,
    because its filters are otherwise contains matches too (`sv03` would also match `sv03.5`).

    Each result is a dict with id, local_id, name and tile_image. The full list for each distinct
    filter combination is fetched once and cached for 24 hours; callers paginate it themselves.
    """
    params = {}
    if name.strip():
        params["name"] = name.strip().lower()
    if set_id:
        params["set.id"] = f"eq:{set_id}"
    if rarity:
        params["rarity"] = f"eq:{rarity}"
    key = "tcgdex:search:" + hashlib.sha256(urlencode(sorted(params.items())).encode()).hexdigest()
    cards = cache.get(key)
    if cards is None:
        try:
            cards = _fetch("cards", _brief_cards, params=params, probe=probe)
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


def card_detail(card_id, probe=False):
    """Return one card's details, cached for 24 hours. Raises NotFound for an unknown ID.

    The result has id, local_id, name, set_id, set_name, rarity, image (the base URL),
    tile_image, prices_updated (TCGplayer's ISO timestamp, or None) and variants.
    """
    key = f"tcgdex:card:{card_id}"
    card = cache.get(key)
    if card is None:
        card = _fetch(f"cards/{quote(card_id, safe='')}", _card_detail, probe=probe)
        cache.set(key, card, CARD_CACHE_SECONDS)
    return card


def _card_detail(data):
    tcgplayer = (data.get("pricing") or {}).get("tcgplayer") or {}
    return {
        "id": data["id"],
        "local_id": data.get("localId") or "",
        "name": data["name"],
        "set_id": data["set"]["id"],
        "set_name": data["set"]["name"],
        "rarity": data.get("rarity") or "",
        "image": data.get("image"),
        "tile_image": image_url(data.get("image"), "low"),
        "prices_updated": tcgplayer.get("updated"),
        "variants": _variants(data.get("variants"), tcgplayer),
    }


def _variants(flags, tcgplayer):
    """The variants whose TCGdex flag is true, in display order, each with its market price.

    TCGdex is community-maintained, so a card may arrive with no flags or none set; it then
    gets Normal rather than an empty (unusable) variant list or an error.
    """
    if not isinstance(flags, dict):
        flags = {}
    found = [row for row in VARIANTS if flags.get(row[0]) is True] or [VARIANTS[0]]
    return [
        {"code": code, "label": label, "price": _market_price(tcgplayer, keys)}
        for _flag, code, label, keys in found
    ]


def _market_price(tcgplayer, keys):
    """The first TCGplayer market price (USD) found under `keys`, as a Decimal, or None."""
    for key in keys:
        price = (tcgplayer.get(key) or {}).get("marketPrice")
        if isinstance(price, int | float) and not isinstance(price, bool):
            # Go through str so 0.28 stays 0.28 instead of the float's binary expansion.
            return Decimal(str(price)).quantize(CENTS)
    return None


def image_url(base, quality="high"):
    """TCGdex image URLs have no suffix; add the quality ("low" or "high") and webp extension."""
    return f"{base}/{quality}.webp" if base else None


def set_groups(probe=False):
    """Return the set dropdown options: [{"name": series name, "sets": [{"id", "name"}]}].

    Series are ordered newest first by release date, and so are the sets inside each one. The
    set list itself doesn't say which series a set belongs to, so each series' detail is fetched
    (concurrently, since there are about 21). The result is cached for 24 hours.
    """
    groups = cache.get(SET_GROUPS_KEY)
    if groups is None:
        groups = _guarded(_load_set_groups, probe)
        cache.set(SET_GROUPS_KEY, groups, OPTIONS_CACHE_SECONDS)
    return groups


def rarities(probe=False):
    """Return every rarity name, alphabetical (ignoring case), cached for 24 hours."""
    names = cache.get(RARITIES_KEY)
    if names is None:
        names = _fetch("rarities", _sorted_names, probe=probe)
        cache.set(RARITIES_KEY, names, OPTIONS_CACHE_SECONDS)
    return names


def _sorted_names(data):
    if not isinstance(data, list) or not all(isinstance(name, str) for name in data):
        raise TypeError("expected a list of names")
    return sorted(data, key=str.casefold)


def _load_set_groups():
    series = _request_json("series", None)
    paths = [f"series/{brief['id']}" for brief in series]
    try:
        with ThreadPoolExecutor(max_workers=SERIES_FETCH_WORKERS) as pool:
            details = list(pool.map(lambda path: _request_json(path, None), paths))
    except NotFound as exc:
        raise ProviderUnavailable("A listed series has no detail") from exc

    details.sort(key=lambda detail: detail.get("releaseDate") or "", reverse=True)
    return [
        {
            "name": detail["name"],
            "sets": [{"id": item["id"], "name": item["name"]} for item in reversed(detail["sets"])],
        }
        for detail in details
        if detail["sets"]
    ]
