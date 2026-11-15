import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

PASSWORD = "Sturdy-Pass-9431"


@pytest.fixture
def ash(db):
    return User.objects.create_user(username="ash", email="ash@example.com", password=PASSWORD)


def test_custom_user_model_is_in_use():
    assert User._meta.label == "accounts.User"


@pytest.mark.django_db
def test_signup_rejects_username_already_taken(client, ash):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "ash",
            "email": "another@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert "username" in response.context["form"].errors
    assert b"A user with that username already exists." in response.content
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_signup_requires_email(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "ash", "email": "", "password1": PASSWORD, "password2": PASSWORD},
    )

    assert response.status_code == 200
    assert "email" in response.context["form"].errors
    assert not User.objects.exists()


def test_sign_in_redirects_to_collection(client, ash):
    response = client.post(reverse("login"), {"username": "ash", "password": PASSWORD})

    assert response.status_code == 302
    assert response.url == reverse("collection:index")
    assert client.session.get("_auth_user_id") == str(ash.pk)


def test_sign_in_returns_to_the_requested_page(client, ash):
    wishlist = reverse("collection:wishlist")

    response = client.post(
        f"{reverse('login')}?next={wishlist}",
        {"username": "ash", "password": PASSWORD, "next": wishlist},
    )

    assert response.status_code == 302
    assert response.url == wishlist


def test_sign_in_with_wrong_password_shows_error(client, ash):
    response = client.post(reverse("login"), {"username": "ash", "password": "wrong"})

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert "_auth_user_id" not in client.session


def test_sign_out_ends_the_session(client, ash):
    client.force_login(ash)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == reverse("login")
    assert "_auth_user_id" not in client.session
    assert client.get(reverse("collection:index")).status_code == 302


def test_signed_in_user_can_open_protected_pages(client, ash):
    client.force_login(ash)

    for name in ("collection:index", "collection:wishlist", "accounts:account"):
        assert client.get(reverse(name)).status_code == 200
