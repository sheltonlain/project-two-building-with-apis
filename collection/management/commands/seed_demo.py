"""Seed demo users and a demo collection for trying the app by hand. Makes no TCGdex calls."""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import Card, CardVariant
from collection.models import OwnedCard, Wish

DEMO_PASSWORD = "pokedex-demo"
MAIN_USER = "demo"  # owns the big collection
OTHER_USER = "misty"  # owns a few cards, for checking that users never see each other's data

SETS = {
    "sv03.5": ("151", "Scarlet & Violet", "https://assets.tcgdex.net/en/sv/sv03.5"),
    "base1": ("Base Set", "Base", "https://assets.tcgdex.net/en/base/base1"),
}

# (TCGdex ID, name, rarity, {variant: TCGplayer price or None})
CARDS = [
    ("sv03.5-001", "Bulbasaur", "Common", {"normal": "0.12", "reverse": "0.45"}),
    ("sv03.5-002", "Ivysaur", "Uncommon", {"normal": "0.15", "reverse": "0.40"}),
    ("sv03.5-003", "Venusaur ex", "Double rare", {"holo": "3.10"}),
    ("sv03.5-004", "Charmander", "Common", {"normal": "0.30", "reverse": "0.90"}),
    ("sv03.5-005", "Charmeleon", "Uncommon", {"normal": "0.20", "reverse": "0.55"}),
    ("sv03.5-006", "Charizard ex", "Double rare", {"holo": "12.75"}),
    ("sv03.5-007", "Squirtle", "Common", {"normal": "0.18", "reverse": "0.60"}),
    ("sv03.5-009", "Blastoise ex", "Double rare", {"holo": "4.20"}),
    ("sv03.5-025", "Pikachu", "Common", {"normal": "0.35", "reverse": "1.10"}),
    ("sv03.5-026", "Raichu", "Uncommon", {"normal": "0.14", "reverse": None}),
    ("sv03.5-039", "Jigglypuff", "Common", {"normal": "0.10", "reverse": "0.35"}),
    ("sv03.5-052", "Meowth", "Common", {"normal": None, "reverse": "0.30"}),
    ("sv03.5-054", "Psyduck", "Common", {"normal": "0.09", "reverse": "0.32"}),
    ("sv03.5-063", "Abra", "Common", {"normal": "0.11", "reverse": "0.38"}),
    ("sv03.5-092", "Gastly", "Common", {"normal": "0.13", "reverse": "0.42"}),
    ("sv03.5-094", "Gengar", "Rare", {"normal": "0.85", "reverse": "1.95"}),
    ("sv03.5-129", "Magikarp", "Common", {"normal": "0.08", "reverse": "0.25"}),
    ("sv03.5-130", "Gyarados", "Rare", {"normal": "0.60", "reverse": "1.40"}),
    ("sv03.5-133", "Eevee", "Common", {"normal": "0.40", "reverse": "1.25"}),
    ("sv03.5-143", "Snorlax", "Uncommon", {"normal": "0.25", "reverse": "0.70"}),
    ("sv03.5-147", "Dratini", "Common", {"normal": "0.12", "reverse": "0.44"}),
    ("sv03.5-150", "Mewtwo", "Rare", {"normal": "0.95", "reverse": "2.10"}),
    ("sv03.5-151", "Mew ex", "Double rare", {"holo": "5.80"}),
    ("base1-2", "Blastoise", "Rare", {"holo": "145.00", "first_edition": None}),
    ("base1-4", "Charizard", "Rare", {"holo": "420.00", "first_edition": None}),
    ("base1-15", "Venusaur", "Rare", {"holo": "110.00", "first_edition": None}),
    ("base1-44", "Bulbasaur", "Common", {"normal": "2.50", "first_edition": "18.00"}),
    ("base1-46", "Charmander", "Common", {"normal": "4.75", "first_edition": "32.00"}),
    ("base1-58", "Pikachu", "Common", {"normal": "3.90", "first_edition": "25.00"}),
    ("base1-63", "Squirtle", "Common", {"normal": "3.25", "first_edition": None}),
]

# (TCGdex ID, variant, quantity, notes), newest first: each entry is dated a day before the last.
DEMO_COLLECTION = [
    ("sv03.5-025", "reverse", 2, "Pulled from my first 151 booster box"),
    ("sv03.5-006", "holo", 1, "Trade target? Misty offered her Blastoise ex"),
    ("sv03.5-025", "normal", 4, ""),
    ("sv03.5-001", "normal", 3, ""),
    ("sv03.5-001", "reverse", 1, ""),
    ("sv03.5-004", "normal", 2, ""),
    ("sv03.5-007", "normal", 2, "trade target"),
    ("sv03.5-003", "holo", 1, ""),
    ("sv03.5-009", "holo", 1, ""),
    ("sv03.5-026", "reverse", 1, "No TCGplayer price yet"),
    ("sv03.5-052", "normal", 5, ""),
    ("sv03.5-054", "normal", 6, ""),
    ("sv03.5-063", "reverse", 1, ""),
    ("sv03.5-092", "normal", 3, ""),
    ("sv03.5-094", "reverse", 1, "Favourite card in the set"),
    ("sv03.5-129", "normal", 12, "Bulk, keep for decks"),
    ("sv03.5-130", "normal", 1, ""),
    ("sv03.5-133", "normal", 2, ""),
    ("sv03.5-133", "reverse", 1, ""),
    ("sv03.5-143", "normal", 1, ""),
    ("sv03.5-147", "normal", 2, ""),
    ("sv03.5-150", "reverse", 1, ""),
    ("sv03.5-151", "holo", 1, "Bought at the local card shop"),
    ("base1-4", "holo", 1, "Childhood card, slightly played"),
    ("base1-2", "first_edition", 1, "Grandpa's card, never trade"),
    ("base1-15", "holo", 1, ""),
    ("base1-44", "normal", 2, ""),
    ("base1-46", "first_edition", 1, "Trade target"),
    ("base1-58", "normal", 3, ""),
    ("base1-63", "first_edition", 1, ""),
]

OTHER_COLLECTION = [
    ("sv03.5-009", "holo", 2, "Misty's own note"),
    ("sv03.5-054", "reverse", 1, ""),
    ("base1-63", "normal", 4, ""),
]

# (TCGdex ID, variant, notes), newest first like the collections.
DEMO_WISHES = [
    ("base1-4", "first_edition", "The grail"),
    ("sv03.5-094", "normal", "Own the reverse holo already"),
    ("sv03.5-025", "reverse", "A second copy for my binder"),
    ("sv03.5-130", "reverse", ""),
    ("sv03.5-039", "normal", "For my deck"),
]

OTHER_WISHES = [
    ("sv03.5-054", "normal", "Misty's own wish"),
]


def _count(items, singular, plural):
    return f"{len(items)} {singular if len(items) == 1 else plural}"


class Command(BaseCommand):
    help = (
        f"Create demo users ({MAIN_USER!r} and {OTHER_USER!r}, password {DEMO_PASSWORD!r}) with "
        "demo collections and wishlists. Re-running resets both users' collections and "
        "wishlists. Only runs with DEBUG on."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even when DEBUG is off (don't, in production).",
        )

    def handle(self, *args, force=False, **options):
        if not settings.DEBUG and not force:
            raise CommandError("seed_demo only runs with DEBUG on. Pass --force to run anyway.")
        with transaction.atomic():
            variants = self.seed_cards()
            self.seed_user(MAIN_USER, DEMO_COLLECTION, DEMO_WISHES, variants)
            self.seed_user(OTHER_USER, OTHER_COLLECTION, OTHER_WISHES, variants)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {_count(DEMO_COLLECTION, 'entry', 'entries')} and "
                f"{_count(DEMO_WISHES, 'wish', 'wishes')} for {MAIN_USER!r}, and "
                f"{_count(OTHER_COLLECTION, 'entry', 'entries')} and "
                f"{_count(OTHER_WISHES, 'wish', 'wishes')} for {OTHER_USER!r}. "
                "Sign in as either user with "
                f"password {DEMO_PASSWORD!r}."
            )
        )

    def seed_cards(self):
        """Store the demo cards and their variants, returning {(card ID, variant): CardVariant}."""
        now = timezone.now()
        variants = {}
        for index, (card_id, name, rarity, prices) in enumerate(CARDS):
            set_id, local_id = card_id.rsplit("-", 1)
            set_name, series, image_base = SETS[set_id]
            card, _ = Card.objects.update_or_create(
                tcgdex_id=card_id,
                defaults={
                    "name": name,
                    "set_id": set_id,
                    "set_name": set_name,
                    "series": series,
                    "rarity": rarity,
                    "local_id": local_id,
                    "image": f"{image_base}/{local_id}",
                },
            )
            for code, price in prices.items():
                variants[card_id, code], _ = CardVariant.objects.update_or_create(
                    card=card,
                    variant=code,
                    defaults={
                        "market_price": Decimal(price) if price else None,
                        "price_updated": now - timedelta(days=index % 5),
                    },
                )
        return variants

    def seed_user(self, username, entries, wishes, variants):
        user, _ = get_user_model().objects.get_or_create(
            username=username, defaults={"email": f"{username}@example.com"}
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        Wish.objects.filter(user=user).delete()
        OwnedCard.objects.filter(user=user).delete()
        now = timezone.now()
        for days_ago, (card_id, code, quantity, notes) in enumerate(entries):
            owned = OwnedCard.objects.create(
                user=user, variant=variants[card_id, code], quantity=quantity, notes=notes
            )
            # created is auto_now_add, so the spread-out "date added" is set afterwards.
            OwnedCard.objects.filter(pk=owned.pk).update(created=now - timedelta(days=days_ago))
        for days_ago, (card_id, code, notes) in enumerate(wishes):
            wish = Wish.objects.create(user=user, variant=variants[card_id, code], notes=notes)
            Wish.objects.filter(pk=wish.pk).update(created=now - timedelta(days=days_ago))
