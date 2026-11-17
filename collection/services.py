"""The app's business rules. Website views and the API both call these, so they always agree."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Min, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from catalog import tcgdex
from catalog.models import Card, CardVariant

from .models import OwnedCard, Wish

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
    """Add one copy of a card variant to the user's collection and return their OwnedCard.

    If the user has an active wish for that variant, it is fulfilled and linked to the OwnedCard;
    the returned OwnedCard's `fulfilled_wish` is that wish, or None.
    """
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
        owned.fulfilled_wish = _fulfill_wish(owned)
    return owned


def _fulfill_wish(owned):
    """Fulfill the user's active wish for the OwnedCard's variant, if any, and return it."""
    wish = Wish.objects.filter(
        user=owned.user_id, variant=owned.variant_id, fulfilled_at__isnull=True
    ).first()
    if wish is not None:
        wish.fulfilled_at = timezone.now()
        wish.fulfilled_by = owned
        wish.save(update_fields=["fulfilled_at", "fulfilled_by"])
    return wish


def add_wish(user, card_id, variant, probe=False):
    """Wish for a card variant. Returns (wish, created); an active wish for the same variant is
    returned, not duplicated."""
    card = get_or_create_card(card_id, probe=probe)
    card_variant = card.variants.filter(variant=variant).first()
    if card_variant is None:
        raise UnsupportedVariant(f"{card.name} doesn't come in that variant.")
    return Wish.objects.get_or_create(user=user, variant=card_variant, fulfilled_at__isnull=True)


def active_wishes(user):
    """The user's wishes that haven't been fulfilled, newest first."""
    return (
        Wish.objects.filter(user=user, fulfilled_at__isnull=True)
        .select_related("variant__card")
        .order_by("-created", "-pk")
    )


def fulfilled_wishes(user):
    """The user's fulfilled wishes that haven't been dismissed yet, most recently fulfilled
    first."""
    return (
        Wish.objects.filter(user=user, fulfilled_at__isnull=False)
        .select_related("variant__card")
        .order_by("-fulfilled_at", "-pk")
    )


def wished_variants(user, card_id):
    """The variant codes of one card that the user has an active wish for."""
    wishes = active_wishes(user).filter(variant__card__tcgdex_id=card_id)
    return set(wishes.values_list("variant__variant", flat=True))


def remove_wish(wish):
    """Delete a wish. Returns what undo_wish_removal() needs to put it back, as JSON-safe data
    (it is kept in the session)."""
    record = {"variant": wish.variant_id, "notes": wish.notes, "created": wish.created.isoformat()}
    wish.delete()
    return record


def undo_wish_removal(user, record):
    """Put back a wish removed by remove_wish(), with its notes and original date added, so it
    returns to its old place on the wishlist. If the user has wished for that variant again
    since, that wish is kept as it is. Returns the active wish."""
    with transaction.atomic():
        wish, created = Wish.objects.get_or_create(
            user=user,
            variant_id=record["variant"],
            fulfilled_at__isnull=True,
            defaults={"notes": record["notes"]},
        )
        if created:
            Wish.objects.filter(pk=wish.pk).update(created=parse_datetime(record["created"]))
            wish.refresh_from_db()
    return wish


def owned_quantities(user, card_id):
    """{variant code: quantity} for the variants of one card that the user owns."""
    rows = OwnedCard.objects.filter(user=user, variant__card__tcgdex_id=card_id)
    return dict(rows.values_list("variant__variant", "quantity"))


def restore_wish(owned):
    """Make the wish most recently fulfilled by this OwnedCard active again and return it.

    If the user already has an active wish for that variant, the fulfilled one is deleted
    instead (there is only one active wish per variant) and None is returned. Returns None when
    no wish is linked to the entry.
    """
    wish = owned.fulfilled_wishes.order_by("-fulfilled_at", "-pk").first()
    if wish is None:
        return None
    fulfilled_at = wish.fulfilled_at
    wish = keep_wish(wish)
    if wish is not None:
        wish.fulfilled_at_before = fulfilled_at  # for removal_record(), so Undo can put it back
    return wish


def remove_copy(owned):
    """Remove one copy. Returns the updated OwnedCard, or None if that was the last copy and the
    entry was deleted. The shared Card and CardVariant rows are always kept.

    The most recently fulfilled wish linked to the entry is restored (see restore_wish()); the
    passed-in OwnedCard's `restored_wish` is that wish, or None.
    """
    with transaction.atomic():
        owned.refresh_from_db()
        owned.restored_wish = restore_wish(owned)
        if owned.quantity <= 1:
            owned.delete()
            return None
        owned.quantity = F("quantity") - 1
        owned.save(update_fields=["quantity", "updated"])
        owned.refresh_from_db()
    return owned


# Collection sort keys (prefix "-" for descending) and the field each one sorts on.
COLLECTION_SORT_FIELDS = {
    "name": "variant__card__name",
    "price": "variant__market_price",
    "value": "value",
    "quantity": "quantity",
    "added": "created",
}
DEFAULT_ORDERING = "-added"


def collection_entries(
    user, search="", set_id="", rarity="", variant="", ordering=DEFAULT_ORDERING
):
    """The user's OwnedCard rows, newest first, each annotated with `value` (price × quantity,
    None when the variant has no price).

    `search` matches the card name or the notes, ignoring case; `set_id`, `rarity` and `variant`
    are exact matches. `ordering` is a key of COLLECTION_SORT_FIELDS, "-" first for descending;
    unknown keys fall back to newest first.
    """
    entries = _filter_entries(OwnedCard.objects.filter(user=user), search, set_id, rarity, variant)
    return (
        entries.select_related("variant__card")
        .annotate(
            value=ExpressionWrapper(
                F("quantity") * F("variant__market_price"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by(_sort(COLLECTION_SORT_FIELDS, ordering), "-created", "-pk")
    )


def _filter_entries(entries, search, set_id, rarity, variant):
    """Filter OwnedCard or Wish rows: `search` matches the card name or the notes, ignoring
    case; `set_id`, `rarity` and `variant` are exact matches."""
    if search:
        entries = entries.filter(
            Q(variant__card__name__icontains=search) | Q(notes__icontains=search)
        )
    if set_id:
        entries = entries.filter(variant__card__set_id=set_id)
    if rarity:
        entries = entries.filter(variant__card__rarity=rarity)
    if variant:
        entries = entries.filter(variant__variant=variant)
    return entries


def _sort(sort_fields, ordering):
    """The order_by expression for a sort key ("-" first for descending); unknown keys mean
    newest first. Empty values (no price) go last in both directions."""
    sort_field = sort_fields.get(ordering.removeprefix("-"))
    if sort_field is None:
        ordering, sort_field = DEFAULT_ORDERING, sort_fields["added"]
    sort = F(sort_field)
    return sort.desc(nulls_last=True) if ordering.startswith("-") else sort.asc(nulls_last=True)


# Wishlist sort keys (prefix "-" for descending) and the field each one sorts on.
WISH_SORT_FIELDS = {
    "name": "variant__card__name",
    "price": "variant__market_price",
    "added": "created",
}


def wish_entries(user, search="", set_id="", rarity="", variant="", ordering=DEFAULT_ORDERING):
    """The user's active wishes, filtered like collection_entries(). `ordering` is a key of
    WISH_SORT_FIELDS, "-" first for descending; unknown keys fall back to newest first."""
    wishes = _filter_entries(active_wishes(user), search, set_id, rarity, variant)
    return wishes.order_by(_sort(WISH_SORT_FIELDS, ordering), "-created", "-pk")


def fulfilled_wish_entries(user, search="", set_id="", rarity="", variant=""):
    """The user's fulfilled wishes awaiting dismissal, filtered like collection_entries(), most
    recently fulfilled first."""
    return _filter_entries(fulfilled_wishes(user), search, set_id, rarity, variant)


def wishlist_filter_options(user):
    """The filter choices for the user's wishlist, drawn only from their own wishes (active and
    fulfilled), in the same shape as collection_filter_options()."""
    return _filter_options(
        Card.objects.filter(variants__wishes__user=user),
        CardVariant.objects.filter(wishes__user=user),
    )


def _filter_options(cards, card_variants):
    """Set, rarity and variant filter choices from the given Card and CardVariant rows."""
    cards = cards.distinct()
    sets = cards.order_by("set_name", "set_id").values_list("set_id", "set_name").distinct()
    rarities = cards.exclude(rarity="").order_by("rarity").values_list("rarity", flat=True)
    codes = set(card_variants.values_list("variant", flat=True).distinct())
    return {
        "sets": list(sets),
        "rarities": list(rarities.distinct()),
        "variants": [(code, label) for code, label in CardVariant.Variant.choices if code in codes],
    }


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


def removal_record(owned, removed, restored_wish=None):
    """What undo_removal() needs to put back `removed` copies of an entry, as JSON-safe data
    (it is kept in the session). `restored_wish` is the wish the removal made active again, if
    any; Undo fulfills it again."""
    record = {
        "variant": owned.variant_id,
        "removed": removed,
        "notes": owned.notes,
        "created": owned.created.isoformat(),
    }
    if restored_wish is not None:
        record["wish"] = {
            "pk": restored_wish.pk,
            "fulfilled_at": restored_wish.fulfilled_at_before.isoformat(),
        }
    return record


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
        if wish := record.get("wish"):
            # Fulfill the wish the removal restored again, unless the user has since dealt with
            # it (removed it, or it was fulfilled by something else).
            Wish.objects.filter(pk=wish["pk"], user=user, fulfilled_at__isnull=True).update(
                fulfilled_at=parse_datetime(wish["fulfilled_at"]), fulfilled_by=owned
            )
    return owned


def collection_filter_options(user):
    """The filter choices for the user's collection, drawn only from their own rows:
    {"sets": [(set ID, set name)], "rarities": [rarity], "variants": [(code, label)]}."""
    return _filter_options(
        Card.objects.filter(variants__owned__user=user),
        CardVariant.objects.filter(owned__user=user),
    )


def keep_wish(wish):
    """Keep wishing for a fulfilled wish's variant: make it active again and return it. The copy
    that fulfilled it stays.

    If the user has an active wish for that variant already, that one is kept and the fulfilled
    wish is deleted (there is only one active wish per variant); None is returned.
    """
    with transaction.atomic():
        if Wish.objects.filter(
            user=wish.user_id, variant=wish.variant_id, fulfilled_at__isnull=True
        ).exists():
            wish.delete()
            return None
        wish.fulfilled_at = None
        wish.fulfilled_by = None
        wish.save(update_fields=["fulfilled_at", "fulfilled_by"])
    return wish


def dismiss_wish(wish):
    """OK: delete a fulfilled wish once the user has seen it. The copy stays."""
    wish.delete()
