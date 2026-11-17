from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path("collection/", views.CollectionView.as_view(), name="index"),
    path("collection/<int:pk>/add/", views.EntryAddView.as_view(), name="entry_add"),
    path("collection/<int:pk>/remove/", views.EntryRemoveView.as_view(), name="entry_remove"),
    path("collection/<int:pk>/delete/", views.EntryDeleteView.as_view(), name="entry_delete"),
    path("collection/<int:pk>/undo/", views.EntryUndoView.as_view(), name="entry_undo"),
    path("collection/<int:pk>/notes/", views.EntryNotesView.as_view(), name="entry_notes"),
    path(
        "collection/<int:pk>/notes/delete/",
        views.EntryNotesDeleteView.as_view(),
        name="entry_notes_delete",
    ),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path("wishlist/<int:pk>/remove/", views.WishRemoveView.as_view(), name="wish_remove"),
    path("wishlist/<int:pk>/undo/", views.WishUndoView.as_view(), name="wish_undo"),
    path("wishlist/<int:pk>/got-it/", views.WishGotItView.as_view(), name="wish_got_it"),
    path("wishlist/<int:pk>/keep/", views.WishKeepView.as_view(), name="wish_keep"),
    path("wishlist/<int:pk>/dismiss/", views.WishDismissView.as_view(), name="wish_dismiss"),
    path("wishlist/<int:pk>/notes/", views.WishNotesView.as_view(), name="wish_notes"),
    path(
        "wishlist/<int:pk>/notes/delete/",
        views.WishNotesDeleteView.as_view(),
        name="wish_notes_delete",
    ),
]
