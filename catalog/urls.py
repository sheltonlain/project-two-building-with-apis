from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("search/", views.SearchView.as_view(), name="search"),
    path("search/card/<str:card_id>/", views.TileDetailsView.as_view(), name="tile_details"),
    path("search/card/<str:card_id>/add/", views.TileAddView.as_view(), name="tile_add"),
    path("search/card/<str:card_id>/remove/", views.TileRemoveView.as_view(), name="tile_remove"),
    path("search/card/<str:card_id>/wish/", views.TileWishView.as_view(), name="tile_wish"),
]
