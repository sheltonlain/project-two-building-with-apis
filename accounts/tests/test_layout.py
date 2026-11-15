import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_base_layout_loads_tailwind_css_and_htmx(client):
    html = client.get(reverse("home")).content.decode()

    assert "css/tailwind.css" in html
    assert "htmx.org@" in html
    assert 'hx-headers=\'{"X-CSRFToken"' in html


@pytest.mark.django_db
def test_nav_for_anonymous_visitor_offers_sign_in_and_sign_up(client):
    html = client.get(reverse("home")).content.decode()

    assert reverse("login") in html
    assert reverse("accounts:signup") in html
    assert "Sign out" not in html


@pytest.mark.django_db
def test_nav_for_signed_in_user_shows_their_pages_and_sign_out(client):
    user = User.objects.create_user(username="ash", email="ash@example.com", password="x")
    client.force_login(user)

    html = client.get(reverse("home")).content.decode()

    assert reverse("collection:index") in html
    assert reverse("collection:wishlist") in html
    assert reverse("accounts:account") in html
    assert "Sign out" in html
    assert reverse("accounts:signup") not in html
