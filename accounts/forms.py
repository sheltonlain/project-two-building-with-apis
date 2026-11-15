from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

EMAIL_TAKEN = "An account with this email address already exists."


def ensure_email_available(email, instance=None):
    """Reject an email another account already uses, ignoring case."""
    others = User.objects.filter(email__iexact=email)
    if instance is not None and instance.pk:
        others = others.exclude(pk=instance.pk)
    if others.exists():
        raise forms.ValidationError(EMAIL_TAKEN)
    return email


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        return ensure_email_available(self.cleaned_data["email"])


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email")

    def clean_email(self):
        return ensure_email_available(self.cleaned_data["email"], self.instance)
