from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path("collection/", views.CollectionView.as_view(), name="index"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
]
