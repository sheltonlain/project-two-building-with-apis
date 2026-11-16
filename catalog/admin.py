from django.contrib import admin

from .models import Card, CardVariant


class CardVariantInline(admin.TabularInline):
    model = CardVariant
    extra = 0


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ["tcgdex_id", "name", "set_name", "rarity", "prices"]
    search_fields = ["tcgdex_id", "name"]
    inlines = [CardVariantInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("variants")

    @admin.display(description="Prices (USD)")
    def prices(self, card):
        return ", ".join(
            f"{v.get_variant_display()}: "
            + (f"${v.market_price}" if v.market_price is not None else "No price")
            for v in card.sorted_variants()
        )
