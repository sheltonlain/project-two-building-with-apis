"""Builders for collection tests that need stored cards without going through TCGdex."""

from datetime import UTC, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model

from catalog.models import Card, CardVariant
from collection.models import OwnedCard, Wish


def make_user(username):
    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


def make_card(card_id, name):
    """A stored Card (created if needed) with no variants yet."""
    card, _ = Card.objects.get_or_create(
        tcgdex_id=card_id,
        defaults={
            "name": name,
            "set_id": card_id.split("-")[0],
            "set_name": "151",
            "rarity": "Common",
            "local_id": card_id.split("-")[-1],
            "image": f"https://assets.tcgdex.net/en/sv/sv03.5/{card_id.split('-')[-1]}",
        },
    )
    return card


def make_variant(card_id, name, variant="normal", price=None, updated=None):
    """A stored CardVariant (card and variant created if needed)."""
    card_variant, _ = CardVariant.objects.get_or_create(
        card=make_card(card_id, name),
        variant=variant,
        defaults={
            "market_price": Decimal(price) if price is not None else None,
            "price_updated": updated or datetime(2026, 11, 14, tzinfo=UTC),
        },
    )
    return card_variant


def make_owned(user, card_id, name, variant="normal", price=None, updated=None, quantity=1):
    """A stored Card (created if needed), one CardVariant of it, and the user's OwnedCard."""
    card_variant = make_variant(card_id, name, variant, price, updated)
    return OwnedCard.objects.create(user=user, variant=card_variant, quantity=quantity)


def make_wish(user, card_id, name, variant="normal", price=None, fulfilled_at=None, notes=""):
    """The user's Wish for a stored card variant (created if needed)."""
    return Wish.objects.create(
        user=user,
        variant=make_variant(card_id, name, variant, price),
        fulfilled_at=fulfilled_at,
        notes=notes,
    )
