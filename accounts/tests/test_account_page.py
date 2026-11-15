import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

PASSWORD = "Sturdy-Pass-9431"


@pytest.fixture
def ash(db):
    return User.objects.create_user(username="ash", email="ash@example.com", password=PASSWORD)


def test_user_can_update_their_username_and_email(client, ash):
    client.force_login(ash)

    response = client.post(
        reverse("accounts:account"),
        {"username": "ash_ketchum", "email": "ketchum@example.com"},
    )

    ash.refresh_from_db()
    assert ash.username == "ash_ketchum"
    assert ash.email == "ketchum@example.com"
    assert response.status_code == 302
    assert response.url == reverse("accounts:account")
    assert client.session.get("_auth_user_id") == str(ash.pk)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("username", "misty", "A user with that username already exists."),
        ("email", "MISTY@Example.com", "An account with this email address already exists."),
    ],
)
def test_taken_username_or_email_is_rejected_and_nothing_is_saved(
    client, ash, field, value, message
):
    User.objects.create_user(username="misty", email="misty@example.com", password=PASSWORD)
    client.force_login(ash)
    data = {"username": "ash", "email": "ash@example.com", field: value}

    response = client.post(reverse("accounts:account"), data)

    assert response.status_code == 200
    assert response.context["form"].errors[field] == [message]
    assert message in response.content.decode()
    ash.refresh_from_db()
    assert (ash.username, ash.email) == ("ash", "ash@example.com")


def test_user_can_keep_their_own_email_or_change_its_case(client, ash):
    client.force_login(ash)

    response = client.post(
        reverse("accounts:account"), {"username": "ash", "email": "Ash@example.com"}
    )

    assert response.status_code == 302
    ash.refresh_from_db()
    assert ash.email == "Ash@example.com"


def test_account_page_shows_only_the_signed_in_users_details(client, ash):
    User.objects.create_user(username="misty", email="misty@example.com", password=PASSWORD)
    client.force_login(ash)

    response = client.get(reverse("accounts:account"))

    content = response.content.decode()
    assert response.status_code == 200
    assert response.context["form"].instance == ash
    assert 'value="ash@example.com"' in content
    assert "misty" not in content
    assert reverse("password_change") in content


def test_posting_another_users_id_still_only_edits_the_signed_in_user(client, ash):
    misty = User.objects.create_user(username="misty", email="misty@example.com", password=PASSWORD)
    client.force_login(ash)

    client.post(
        reverse("accounts:account"),
        {"id": misty.pk, "pk": misty.pk, "username": "renamed", "email": "renamed@example.com"},
    )

    misty.refresh_from_db()
    ash.refresh_from_db()
    assert (misty.username, misty.email) == ("misty", "misty@example.com")
    assert (ash.username, ash.email) == ("renamed", "renamed@example.com")


def test_saving_details_shows_a_confirmation(client, ash):
    client.force_login(ash)

    response = client.post(
        reverse("accounts:account"),
        {"username": "ash", "email": "ash@example.com"},
        follow=True,
    )

    assert "Your details were saved." in response.content.decode()


def test_password_change_works_and_keeps_the_user_signed_in(client, ash):
    client.force_login(ash)
    new_password = "Brand-New-Pass-5527"

    response = client.post(
        reverse("password_change"),
        {
            "old_password": PASSWORD,
            "new_password1": new_password,
            "new_password2": new_password,
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("password_change_done")
    ash.refresh_from_db()
    assert ash.check_password(new_password)
    assert client.get(reverse("accounts:account")).status_code == 200


def test_password_change_with_wrong_old_password_is_rejected(client, ash):
    client.force_login(ash)

    response = client.post(
        reverse("password_change"),
        {
            "old_password": "wrong",
            "new_password1": "Brand-New-Pass-5527",
            "new_password2": "Brand-New-Pass-5527",
        },
    )

    assert response.status_code == 200
    assert "old_password" in response.context["form"].errors
    ash.refresh_from_db()
    assert ash.check_password(PASSWORD)


def test_password_change_requires_sign_in(client, db):
    response = client.get(reverse("password_change"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
