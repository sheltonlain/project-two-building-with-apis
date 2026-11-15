from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from . import tcgdex

PAGE_SIZE = 24
FILTERS = ("name", "set", "rarity")


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

        try:
            context["set_groups"] = tcgdex.set_groups()
            context["rarities"] = tcgdex.rarities()
        except tcgdex.ProviderUnavailable:
            context["filters_unavailable"] = True

        if not any(filters.values()):
            context["needs_filter"] = any(key in query for key in FILTERS)
            return context

        try:
            cards = tcgdex.search_cards(filters["name"], filters["set"], filters["rarity"])
        except tcgdex.ProviderUnavailable:
            context["unavailable"] = True
            return context

        page = Paginator(cards, PAGE_SIZE).get_page(query.get("page"))
        context["searched"] = True
        context["page"] = page
        context["page_range"] = page.paginator.get_elided_page_range(page.number)
        return context
