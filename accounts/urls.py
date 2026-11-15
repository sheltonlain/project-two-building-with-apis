from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("accounts/signup/", views.SignUpView.as_view(), name="signup"),
    path("account/", views.AccountView.as_view(), name="account"),
]
