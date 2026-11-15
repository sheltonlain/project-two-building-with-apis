from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("", include("collection.urls")),
    path("admin/", admin.site.urls),
]
