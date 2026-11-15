from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from . import tcgdex

PAGE_SIZE = 24


class SearchView(LoginRequiredMixin, TemplateView):
    """Search the TCGdex catalog. Requires at least one filter (rule #1)."""

    template_name = "catalog/search.html"

    def get_template_names(self):
        # HTMX requests swap just the results; a history restore needs the whole page.
        headers = self.request.headers
        if headers.get("HX-Request") and not headers.get("HX-History-Restore-Request"):
            return ["catalog/_search_panel.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = self.request.GET.get("name", "").strip()
        context["name"] = name
        if not name:
            context["needs_filter"] = "name" in self.request.GET
            return context

        try:
            cards = tcgdex.search_cards(name)
        except tcgdex.ProviderUnavailable:
            context["unavailable"] = True
            return context

        page = Paginator(cards, PAGE_SIZE).get_page(self.request.GET.get("page"))
        context["searched"] = True
        context["page"] = page
        context["page_range"] = page.paginator.get_elided_page_range(page.number)
        return context
