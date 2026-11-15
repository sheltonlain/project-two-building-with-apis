import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

PASSWORD = "Sturdy-Pass-9431"


def signup_data(**overrides):
    data = {
        "username": "ash",
        "email": "ash@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_valid_signup_creates_user_signs_them_in_and_redirects_to_collection(client):
    response = client.post(reverse("accounts:signup"), signup_data())

    user = User.objects.get(username="ash")
    assert user.email == "ash@example.com"
    assert user.check_password(PASSWORD)
    assert response.status_code == 302
    assert response.url == reverse("collection:index")
    assert client.session.get("_auth_user_id") == str(user.pk)


@pytest.mark.django_db
def test_signup_rejects_email_already_taken_ignoring_case(client):
    User.objects.create_user(username="misty", email="misty@example.com", password=PASSWORD)

    response = client.post(
        reverse("accounts:signup"),
        signup_data(username="ash", email="MISTY@Example.com"),
    )

    assert response.status_code == 200
    assert response.context["form"].errors["email"] == [
        "An account with this email address already exists."
    ]
    assert not User.objects.filter(username="ash").exists()
