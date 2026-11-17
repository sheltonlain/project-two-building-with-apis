from rest_framework import serializers

from catalog.models import Card, CardVariant
from collection.models import NOTES_MAX_LENGTH, OwnedCard, Wish


def notes_field():
    return serializers.CharField(max_length=NOTES_MAX_LENGTH, required=False, allow_blank=True)


class CardSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="tcgdex_id")

    class Meta:
        model = Card
        fields = ["id", "name", "set_id", "set_name", "series", "rarity", "local_id", "image"]


class EntrySerializer(serializers.ModelSerializer):
    """Fields shared by collection entries and wishes: the card variant, its price and notes."""

    card = CardSerializer(source="variant.card", read_only=True)
    variant = serializers.CharField(source="variant.variant", read_only=True)
    market_price = serializers.DecimalField(
        source="variant.market_price", max_digits=10, decimal_places=2, read_only=True
    )
    price_updated = serializers.DateTimeField(source="variant.price_updated", read_only=True)


class WishSerializer(EntrySerializer):
    class Meta:
        model = Wish
        fields = [
            "id",
            "card",
            "variant",
            "market_price",
            "price_updated",
            "notes",
            "created",
            "fulfilled_at",
            "fulfilled_by",
        ]
        read_only_fields = fields


class OwnedCardSerializer(EntrySerializer):
    fulfilled_wish = serializers.SerializerMethodField(
        help_text="The wish this request fulfilled, or null."
    )

    class Meta:
        model = OwnedCard
        fields = [
            "id",
            "card",
            "variant",
            "quantity",
            "market_price",
            "price_updated",
            "notes",
            "created",
            "updated",
            "fulfilled_wish",
        ]
        read_only_fields = fields

    def get_fulfilled_wish(self, owned):
        wish = getattr(owned, "fulfilled_wish", None)  # set by services.add_copy
        return WishSerializer(wish).data if wish is not None else None


class NewEntrySerializer(serializers.Serializer):
    """A wishlist create request: a TCGdex card ID, a variant and optional notes."""

    card_id = serializers.CharField(max_length=50)
    variant = serializers.ChoiceField(choices=CardVariant.Variant.choices)
    notes = notes_field()


class NewOwnedCardSerializer(NewEntrySerializer):
    """A collection create request: a wishlist create request plus a quantity (default 1)."""

    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateSerializer(serializers.Serializer):
    """A PATCH request. Only the declared fields may change; anything else (the variant, the
    card) is rejected, because changing it means deleting and re-creating the entry."""

    def validate(self, attrs):
        others = sorted(set(self.initial_data) - set(self.fields))
        if others:
            allowed = " and ".join(self.fields)
            message = (
                f"This can't be changed; only {allowed} can. "
                "Delete the entry and create a new one instead."
            )
            raise serializers.ValidationError({name: [message] for name in others})
        return attrs


class OwnedCardUpdateSerializer(UpdateSerializer):
    quantity = serializers.IntegerField(min_value=0, required=False)
    notes = notes_field()


class WishUpdateSerializer(UpdateSerializer):
    notes = notes_field()
