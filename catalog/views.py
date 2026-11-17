import random

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView

from collection import services
from collection.models import OwnedCard
from collection.views import add_notice, remove_notice

from . import tcgdex
from .models import Card

PAGE_SIZE = 24
FILTERS = ("name", "set", "rarity")
RETRY_SPREAD = 3  # seconds; failed tiles retry up to this long after the breaker closes
USER_RETRY_HEADER = "X-User-Retry"  # sent by Retry/"Try now" buttons, not by automatic loads
TCGDEX_BACK_EVENT = "tcgdex-back"  # tells the page a user retry worked, so other tiles retry too


def is_user_retry(request):
    return request.headers.get(USER_RETRY_HEADER) == "1"


class TCGdexCaller:
    """Calls the TCGdex client, as a user retry (`probe`) if the user asked for one.

    A user retry checks TCGdex even while the circuit breaker is open. Once one call fails, the
    rest of the request stops probing, so a single click costs at most one failed request.
    """

    def __init__(self, request):
        self.probe = is_user_retry(request)

    def __call__(self, function, *args):
        try:
            return function(*args, probe=self.probe)
        except tcgdex.ProviderUnavailable:
            self.probe = False
            raise


class SearchView(LoginRequiredMixin, TemplateView):
    """Search the TCGdex catalog by name, set and rarity. Requires at least one filter (rule #1)."""

    template_name = "catalog/search.html"

    def get_template_names(self):
        # HTMX requests swap just the results; a history restore needs the whole page.
        headers = self.request.headers
        if headers.get("HX-Request") and not headers.get("HX-History-Restore-Request"):
            return ["catalog/_search_panel.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET
        filters = {key: query.get(key, "").strip() for key in FILTERS}
        context["filters"] = filters
        call = TCGdexCaller(self.request)

        try:
            context["set_groups"] = call(tcgdex.set_groups)
            context["rarities"] = call(tcgdex.rarities)
        except tcgdex.ProviderUnavailable:
            context["filters_unavailable"] = True
            self.add_retry_context(context)

        if not any(filters.values()):
            context["needs_filter"] = any(key in query for key in FILTERS)
            return context

        try:
            cards = call(tcgdex.search_cards, filters["name"], filters["set"], filters["rarity"])
        except tcgdex.ProviderUnavailable:
            context["unavailable"] = True
            self.add_retry_context(context)
            return context

        page = Paginator(cards, PAGE_SIZE).get_page(query.get("page"))
        context["searched"] = True
        context["page"] = page
        context["page_range"] = page.paginator.get_elided_page_range(page.number)
        return context

    def add_retry_context(self, context):
        """When to re-submit the search automatically, timed like a failed tile's retry.

        The automatic retry sends the form as it stands (keeping anything typed meanwhile) plus
        the result page that failed, so a failed page 3 comes back as page 3.
        """
        context["retry_delay"] = tcgdex.outage_seconds_left() + random.randint(0, RETRY_SPREAD)
        page = self.request.GET.get("page", "")
        context["retry_page"] = page if page.isdigit() else ""


class TileDetailsView(LoginRequiredMixin, TemplateView):
    """The lower half of one search tile: set, rarity, variant choice, price, and the user's
    Add button or "− N owned +" stepper for the selected variant.

    Each tile loads this separately, so one card failing doesn't affect the others.
    """

    template_name = "catalog/_tile_details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card_id = self.kwargs["card_id"]
        context["card_id"] = card_id
        try:
            card = TCGdexCaller(self.request)(tcgdex.card_detail, card_id)
        except tcgdex.NotFound:
            context["not_found"] = True
            return context
        except tcgdex.ProviderUnavailable:
            # Retry by itself once the breaker closes. The random spread stops every failed tile
            # on the page from hitting TCGdex at the same moment.
            context["unavailable"] = True
            context["retry_url"] = self.request.get_full_path()
            context["retry_delay"] = tcgdex.outage_seconds_left() + random.randint(0, RETRY_SPREAD)
            return context

        services.refresh_stored_card(card)  # the automatic price refresh for saved cards
        self.add_card_context(context, card, self.request.GET.get("variant", ""))
        return context

    def add_card_context(self, context, card, wanted):
        """Fill in the card, the selected variant and what the user owns of it."""
        variants = card["variants"]
        selected = next((v for v in variants if v["code"] == wanted), variants[0])
        owned = services.owned_quantities(self.request.user, card["id"])
        context["card"] = card
        context["selected"] = selected
        context["owned_count"] = owned.get(selected["code"], 0)
        context["owned_summary"] = ", ".join(
            f"{owned[v['code']]} {v['label']}" for v in variants if owned.get(v["code"])
        )
        wished = services.wished_variants(self.request.user, card["id"])
        context["wished"] = selected["code"] in wished
        context["wish_summary"] = ", ".join(v["label"] for v in variants if v["code"] in wished)

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        if is_user_retry(self.request) and "card" in context:
            response["HX-Trigger"] = TCGDEX_BACK_EVENT
        return response


class TileActionView(TileDetailsView):
    """Base for the tile's actions: POST `variant`, get the updated tile back.

    After an action the card is stored locally, so the tile is drawn from the stored Card and
    doesn't depend on TCGdex.
    """

    http_method_names = ["post"]

    def post(self, request, card_id):
        context = {"card_id": card_id}
        variant = request.POST.get("variant", "")
        self.act(context, card_id, variant)
        if "unavailable" not in context and "not_found" not in context:
            card = get_object_or_404(Card, tcgdex_id=card_id)
            self.add_card_context(context, card.as_detail(), variant)
        return self.render_to_response(context)

    def act(self, context, card_id, variant):
        raise NotImplementedError


class TileAddView(TileActionView):
    """ "Add to collection" and the stepper's "+": one more copy of the selected variant."""

    def act(self, context, card_id, variant):
        try:
            owned = services.add_copy(self.request.user, card_id, variant)
        except services.UnsupportedVariant:
            context["error"] = "This card doesn't come in that variant. Pick one from the list."
        except tcgdex.NotFound:
            context["not_found"] = True
        except tcgdex.ProviderUnavailable:
            context["unavailable"] = True
            context["error"] = (
                "We couldn't add this card because TCGdex, the card database, didn't respond. "
                "Try again in a minute."
            )
            context["retry_url"] = reverse("catalog:tile_details", args=[card_id])
            context["retry_delay"] = tcgdex.outage_seconds_left() + random.randint(0, RETRY_SPREAD)
        else:
            label = owned.variant.get_variant_display()
            context["notice"] = add_notice(label, owned)
            context["wish_fulfilled"] = owned.fulfilled_wish is not None
            context["update_nav"] = context["wish_fulfilled"]


class TileRemoveView(TileActionView):
    """The stepper's "−": one copy fewer; the entry is deleted when none are left."""

    def act(self, context, card_id, variant):
        owned = (
            OwnedCard.objects.select_related("variant")
            .filter(user=self.request.user, variant__card__tcgdex_id=card_id)
            .filter(variant__variant=variant)
            .first()
        )
        if owned is None:
            return  # nothing of this variant to remove (e.g. already removed in another tab)
        label = owned.variant.get_variant_display()
        deleted = services.remove_copy(owned) is None
        context["notice"] = remove_notice(label, owned, deleted)
        context["update_nav"] = owned.restored_wish is not None


class TileWishView(TileActionView):
    """Add the selected variant to the user's wishlist."""

    def act(self, context, card_id, variant):
        try:
            wish, created = services.add_wish(self.request.user, card_id, variant)
        except services.UnsupportedVariant:
            context["error"] = "This card doesn't come in that variant. Pick one from the list."
        except tcgdex.NotFound:
            context["not_found"] = True
        except tcgdex.ProviderUnavailable:
            context["unavailable"] = True
            context["error"] = (
                "We couldn't add this card to your wishlist because TCGdex, the card database, "
                "didn't respond. Try again in a minute."
            )
            context["retry_url"] = reverse("catalog:tile_details", args=[card_id])
            context["retry_delay"] = tcgdex.outage_seconds_left() + random.randint(0, RETRY_SPREAD)
        else:
            label = wish.variant.get_variant_display()
            if created:
                context["notice"] = f"Added {label} to your wishlist."
            else:
                context["notice"] = f"{label} is already on your wishlist."
            context["update_nav"] = True
