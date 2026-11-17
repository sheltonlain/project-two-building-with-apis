from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView
from rest_framework.authtoken.models import Token

from .forms import AccountForm, SignUpForm


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(settings.LOGIN_REDIRECT_URL)


class AccountView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edit the signed-in user's own details; there is no pk in the URL."""

    form_class = AccountForm
    template_name = "accounts/account.html"
    success_url = reverse_lazy("accounts:account")
    success_message = "Your details were saved."

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["api_token"], _ = Token.objects.get_or_create(user=self.request.user)
        return context


class RegenerateTokenView(LoginRequiredMixin, View):
    """Replace the user's API token, so the old one stops working at once."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        Token.objects.create(user=request.user)
        messages.success(
            request, "Your API token was regenerated. Programs using the old one need the new one."
        )
        return redirect("accounts:account")
