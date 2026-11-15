from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("search/", views.SearchView.as_view(), name="search"),
]
