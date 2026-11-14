"""Console check that the TCGdex API is reachable and returns useful card data.

Run from the project root:
    uv run python scripts/tcgdex_check.py

TCGdex needs no API key or account, so no credentials are read or sent.
Docs: https://tcgdex.dev
"""

import requests

BASE_URL = "https://api.tcgdex.net/v2"
LANGUAGE = "en"
TIMEOUT_SECONDS = 10
MAX_RESULTS_SHOWN = 20


class TCGdexError(Exception):
    """Raised when a request to TCGdex fails, with a message fit for the user."""


def _get_json(path, params=None):
    """GET a TCGdex path and return the parsed JSON, or raise TCGdexError."""
    url = f"{BASE_URL}/{LANGUAGE}/{path}"
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise TCGdexError(f"TCGdex did not respond within {TIMEOUT_SECONDS} seconds. Try again later.")
    except requests.exceptions.ConnectionError:
        raise TCGdexError("Could not connect to TCGdex. Check your internet connection.")
    except requests.exceptions.RequestException as exc:
        raise TCGdexError(f"The request to TCGdex failed: {exc}")

    if response.status_code == 404:
        return None
    if not response.ok:
        raise TCGdexError(f"TCGdex returned an error (HTTP {response.status_code}). Try again later.")

    try:
        return response.json()
    except ValueError:
        raise TCGdexError("TCGdex sent a response that was not valid JSON.")


def search_cards(name):
    """Return a list of brief card dicts whose name contains `name`."""
    return _get_json("cards", params={"name": name}) or []


def get_card(card_id):
    """Return the full card dict for `card_id`, or None if it does not exist."""
    return _get_json(f"cards/{card_id}")


def image_url(card, quality="high", ext="png"):
    """TCGdex image fields have no file suffix; build a usable image URL."""
    base = card.get("image")
    return f"{base}/{quality}.{ext}" if base else "n/a (no image available)"


def show_results(cards):
    total = len(cards)
    shown = cards[:MAX_RESULTS_SHOWN]
    if total > len(shown):
        print(f"\nFound {total} cards, showing the first {len(shown)}. Try a more specific name to narrow it down.")
    else:
        print(f"\nFound {total} card{'s' if total != 1 else ''}:")
    for number, card in enumerate(shown, start=1):
        print(f"  {number:>2}. {card.get('name', '?')}  ({card.get('id', '?')})")
    return shown


def show_card(card):
    set_info = card.get("set") or {}
    official_count = (set_info.get("cardCount") or {}).get("official")
    card_number = card.get("localId", "?")
    if official_count:
        card_number = f"{card_number}/{official_count}"

    types = ", ".join(card.get("types") or []) or "n/a"
    print("\n" + "=" * 50)
    print(f"  {card.get('name', '?')}")
    print("=" * 50)
    print(f"  ID:          {card.get('id', 'n/a')}")
    print(f"  Set:         {set_info.get('name', 'n/a')}")
    print(f"  Number:      {card_number}")
    print(f"  Rarity:      {card.get('rarity') or 'n/a'}")
    print(f"  Category:    {card.get('category') or 'n/a'}")
    print(f"  HP:          {card.get('hp') or 'n/a'}")
    print(f"  Types:       {types}")
    print(f"  Illustrator: {card.get('illustrator') or 'n/a'}")

    attacks = card.get("attacks") or []
    if attacks:
        print("  Attacks:")
        for attack in attacks:
            cost = ", ".join(attack.get("cost") or []) or "free"
            damage = attack.get("damage", "-")
            print(f"    - {attack.get('name', '?')}  (damage: {damage}, cost: {cost})")
    else:
        print("  Attacks:     n/a")

    print(f"  Image:       {image_url(card)}")
    print("=" * 50)


def choose_card(shown):
    """Ask the user to pick a number from the list. Returns a card dict or None."""
    while True:
        choice = input(f"\nPick a card number (1-{len(shown)}), or press Enter to search again: ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            return shown[int(choice) - 1]
        print(f"Please enter a number from 1 to {len(shown)}.")


def main():
    print("TCGdex API check (no API key needed)")
    while True:
        name = input("\nEnter a Pokemon card name to search (or 'q' to quit): ").strip()
        if not name or name.lower() == "q":
            print("Goodbye!")
            break

        try:
            cards = search_cards(name)
        except TCGdexError as exc:
            print(f"Error: {exc}")
            continue

        if not cards:
            print(f"No cards found matching '{name}'. Check the spelling or try part of the name.")
            continue

        picked = choose_card(show_results(cards))
        if picked is None:
            continue

        try:
            card = get_card(picked["id"])
        except TCGdexError as exc:
            print(f"Error: {exc}")
            continue

        if card is None:
            print(f"TCGdex has no details for card '{picked['id']}'.")
            continue
        show_card(card)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
