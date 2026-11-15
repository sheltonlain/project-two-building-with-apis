from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class CollectionView(LoginRequiredMixin, TemplateView):
    template_name = "collection/collection.html"


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "collection/wishlist.html"
