from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path("collection/", views.CollectionView.as_view(), name="index"),
    path("collection/<int:pk>/add/", views.EntryAddView.as_view(), name="entry_add"),
    path("collection/<int:pk>/remove/", views.EntryRemoveView.as_view(), name="entry_remove"),
    path("collection/<int:pk>/delete/", views.EntryDeleteView.as_view(), name="entry_delete"),
    path("collection/<int:pk>/undo/", views.EntryUndoView.as_view(), name="entry_undo"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path("wishlist/<int:pk>/remove/", views.WishRemoveView.as_view(), name="wish_remove"),
    path("wishlist/<int:pk>/undo/", views.WishUndoView.as_view(), name="wish_undo"),
]
