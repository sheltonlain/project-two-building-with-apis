from django.db import models

from . import tcgdex

VARIANT_ORDER = [code for _flag, code, _label, _keys in tcgdex.VARIANTS]


class Card(models.Model):
    """One TCGdex card, shared by every user. Created the first time anyone saves it, and kept
    even when no one references it any more, so it also serves as a local cache."""

    tcgdex_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    set_id = models.CharField(max_length=50)
    set_name = models.CharField(max_length=200)
    series = models.CharField(max_length=200, blank=True)
    rarity = models.CharField(max_length=100, blank=True)
    local_id = models.CharField(max_length=20, blank=True)
    image = models.URLField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.name} ({self.tcgdex_id})"

    @property
    def tile_image(self):
        return tcgdex.image_url(self.image, "low")

    def sorted_variants(self):
        """This card's variants in the app's display order (Normal, Reverse holo, ...)."""
        return sorted(self.variants.all(), key=lambda v: VARIANT_ORDER.index(v.variant))

    def as_detail(self):
        """The stored card in the same shape as tcgdex.card_detail(), so templates that show a
        TCGdex card can show a stored one without asking TCGdex."""
        return {
            "id": self.tcgdex_id,
            "local_id": self.local_id,
            "name": self.name,
            "set_id": self.set_id,
            "set_name": self.set_name,
            "rarity": self.rarity,
            "image": self.image or None,
            "tile_image": self.tile_image,
            "variants": [
                {"code": v.variant, "label": v.get_variant_display(), "price": v.market_price}
                for v in self.sorted_variants()
            ],
        }


class CardVariant(models.Model):
    """A variant a card exists in, with its TCGplayer market price. A card's CardVariant rows
    are its allowed variants."""

    class Variant(models.TextChoices):
        NORMAL = "normal", "Normal"
        REVERSE = "reverse", "Reverse holo"
        HOLO = "holo", "Holo"
        FIRST_EDITION = "first_edition", "1st Edition"
        W_PROMO = "w_promo", "W Promo"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="variants")
    variant = models.CharField(max_length=20, choices=Variant)
    market_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["card", "variant"], name="unique_card_variant"),
        ]

    def __str__(self):
        return f"{self.card} · {self.get_variant_display()}"
