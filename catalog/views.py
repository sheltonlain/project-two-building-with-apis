import random

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from . import tcgdex

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

        if not any(filters.values()):
            context["needs_filter"] = any(key in query for key in FILTERS)
            return context

        try:
            cards = call(tcgdex.search_cards, filters["name"], filters["set"], filters["rarity"])
        except tcgdex.ProviderUnavailable:
            context["unavailable"] = True
            return context

        page = Paginator(cards, PAGE_SIZE).get_page(query.get("page"))
        context["searched"] = True
        context["page"] = page
        context["page_range"] = page.paginator.get_elided_page_range(page.number)
        return context


class TileDetailsView(LoginRequiredMixin, TemplateView):
    """The lower half of one search tile: set, rarity, variant choice and price.

    Each tile loads this separately, so one card failing doesn't affect the others.
    """

    template_name = "catalog/_tile_details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card_id = self.kwargs["card_id"]
        wanted = self.request.GET.get("variant", "")
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

        variants = card["variants"]
        context["card"] = card
        context["selected"] = next((v for v in variants if v["code"] == wanted), variants[0])
        return context

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        if is_user_retry(self.request) and "card" in context:
            response["HX-Trigger"] = TCGDEX_BACK_EVENT
        return response
