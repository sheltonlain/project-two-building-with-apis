from django.contrib import admin

from .models import OwnedCard


@admin.register(OwnedCard)
class OwnedCardAdmin(admin.ModelAdmin):
    list_display = ["user", "variant", "quantity", "price", "updated"]
    list_select_related = ["user", "variant__card"]
    raw_id_fields = ["variant"]

    @admin.display(description="Price (USD)", ordering="variant__market_price")
    def price(self, owned):
        price = owned.variant.market_price
        return f"${price}" if price is not None else "No price"
