"""Builders for collection tests that need stored cards without going through TCGdex."""

from datetime import UTC, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model

from catalog.models import Card, CardVariant
from collection.models import OwnedCard


def make_user(username):
    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


def make_owned(user, card_id, name, variant="normal", price=None, updated=None, quantity=1):
    """A stored Card (created if needed), one CardVariant of it, and the user's OwnedCard."""
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
    card_variant = CardVariant.objects.create(
        card=card,
        variant=variant,
        market_price=Decimal(price) if price is not None else None,
        price_updated=updated or datetime(2026, 11, 14, tzinfo=UTC),
    )
    return OwnedCard.objects.create(user=user, variant=card_variant, quantity=quantity)
