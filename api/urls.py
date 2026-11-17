from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("collection", views.CollectionViewSet, basename="collection")
router.register("wishlist", views.WishlistViewSet, basename="wishlist")

urlpatterns = [path("", include(router.urls))]
