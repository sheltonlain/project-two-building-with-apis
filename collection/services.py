"""The app's business rules. Website views and the API both call these, so they always agree."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Min, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from catalog import tcgdex
from catalog.models import Card, CardVariant

from .models import OwnedCard

CENTS = Decimal("0.01")


class UnsupportedVariant(ValueError):
    """The card doesn't exist in the requested variant."""


def get_or_create_card(card_id, probe=False):
    """The stored Card for a TCGdex card ID, fetching and storing it first if it's new locally.

    Raises tcgdex.NotFound for an unknown ID and tcgdex.ProviderUnavailable when TCGdex can't be
    reached and the card isn't stored yet.
    """
    card = Card.objects.filter(tcgdex_id=card_id).first()
    if card is None:
        card = _store_card(tcgdex.card_detail(card_id, probe=probe))
    return card


def _store_card(detail):
    updated = _parse_time(detail.get("prices_updated"))
    with transaction.atomic():
        card, created = Card.objects.get_or_create(
            tcgdex_id=detail["id"],
            defaults={
                "name": detail["name"],
                "set_id": detail["set_id"],
                "set_name": detail["set_name"],
                "series": tcgdex.cached_series_name(detail["set_id"]),
                "rarity": detail["rarity"],
                "local_id": detail["local_id"],
                "image": detail["image"] or "",
            },
        )
        if created:
            CardVariant.objects.bulk_create(
                CardVariant(
                    card=card,
                    variant=variant["code"],
                    market_price=variant["price"],
                    price_updated=updated,
                )
                for variant in detail["variants"]
            )
    return card


def _parse_time(value):
    """TCGplayer's price timestamp, or now if it's missing or unreadable."""
    try:
        parsed = parse_datetime(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    return parsed or timezone.now()


def add_copy(user, card_id, variant, probe=False):
    """Add one copy of a card variant to the user's collection and return their OwnedCard."""
    card = get_or_create_card(card_id, probe=probe)
    card_variant = card.variants.filter(variant=variant).first()
    if card_variant is None:
        raise UnsupportedVariant(f"{card.name} doesn't come in that variant.")
    with transaction.atomic():
        owned, created = OwnedCard.objects.get_or_create(user=user, variant=card_variant)
        if not created:
            owned.quantity = F("quantity") + 1
            owned.save(update_fields=["quantity", "updated"])
            owned.refresh_from_db()
    return owned


def owned_quantities(user, card_id):
    """{variant code: quantity} for the variants of one card that the user owns."""
    rows = OwnedCard.objects.filter(user=user, variant__card__tcgdex_id=card_id)
    return dict(rows.values_list("variant__variant", "quantity"))


def remove_copy(owned):
    """Remove one copy. Returns the updated OwnedCard, or None if that was the last copy and the
    entry was deleted. The shared Card and CardVariant rows are always kept."""
    with transaction.atomic():
        owned.refresh_from_db()
        if owned.quantity <= 1:
            owned.delete()
            return None
        owned.quantity = F("quantity") - 1
        owned.save(update_fields=["quantity", "updated"])
        owned.refresh_from_db()
    return owned


def collection_entries(user):
    """The user's OwnedCard rows, newest first, each annotated with `value` (price × quantity,
    None when the variant has no price)."""
    return (
        OwnedCard.objects.filter(user=user)
        .select_related("variant__card")
        .annotate(
            value=ExpressionWrapper(
                F("quantity") * F("variant__market_price"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("-created", "-pk")
    )


def delete_entry(owned):
    """Remove every copy of an entry. The shared Card and CardVariant rows are kept."""
    owned.delete()


def collection_value(user):
    """The user's collection value, computed in the database.

    Returns {"total": price × quantity summed over priced entries, "unpriced": how many entries
    have no price, "as_of": the oldest price-updated time among priced entries (None if none)}.
    """
    priced = Q(variant__market_price__isnull=False)
    value = OwnedCard.objects.filter(user=user).aggregate(
        total=Sum(
            F("quantity") * F("variant__market_price"),
            filter=priced,
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        unpriced=Count("pk", filter=~priced),
        as_of=Min("variant__price_updated", filter=priced),
    )
    value["total"] = (value["total"] or Decimal("0")).quantize(CENTS)
    return value


def removal_record(owned, removed):
    """What undo_removal() needs to put back `removed` copies of an entry, as JSON-safe data
    (it is kept in the session)."""
    return {
        "variant": owned.variant_id,
        "removed": removed,
        "notes": owned.notes,
        "created": owned.created.isoformat(),
    }


def undo_removal(user, record):
    """Put back the copies described by removal_record(). If the entry was deleted, it comes back
    with its notes and original date added, so it returns to its old place in the collection."""
    with transaction.atomic():
        owned, created = OwnedCard.objects.get_or_create(
            user=user,
            variant_id=record["variant"],
            defaults={"quantity": record["removed"], "notes": record["notes"]},
        )
        if created:
            OwnedCard.objects.filter(pk=owned.pk).update(created=parse_datetime(record["created"]))
        else:
            owned.quantity = F("quantity") + record["removed"]
            owned.save(update_fields=["quantity", "updated"])
        owned.refresh_from_db()
    return owned
