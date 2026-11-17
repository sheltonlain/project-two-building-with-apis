"""Who may use the API: a valid token or a signed-in session, and nobody else."""

import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from collection.tests.helpers import make_owned, make_user

ENDPOINTS = ["/api/collection/", "/api/wishlist/"]


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.mark.parametrize("url", ENDPOINTS)
def test_requests_without_a_token_or_session_are_rejected(ash, url):
    client = APIClient()

    assert client.get(url).status_code == 401
    assert client.post(url, {"card_id": "x", "variant": "normal"}).status_code == 401


@pytest.mark.parametrize("url", ENDPOINTS)
def test_an_invalid_token_is_rejected(ash, url):
    client = APIClient(HTTP_AUTHORIZATION="Token not-a-real-token")

    assert client.get(url).status_code == 401


def test_a_token_in_the_header_authenticates_as_its_user(ash):
    make_owned(ash, "sv03.5-025", "Pikachu")
    token = Token.objects.create(user=ash)
    client = APIClient(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.get("/api/collection/")

    assert response.status_code == 200
    assert response.json()["results"][0]["card"]["name"] == "Pikachu"


def test_the_website_session_works_in_the_browsable_api(client, ash):
    client.force_login(ash)

    response = client.get("/api/collection/", HTTP_ACCEPT="text/html")

    assert response.status_code == 200
    assert "Collection" in response.content.decode()


def test_the_account_page_shows_the_users_api_token(client, ash):
    client.force_login(ash)

    response = client.get(reverse("accounts:account"))

    token = Token.objects.get(user=ash)
    assert token.key in response.content.decode()
    assert "Regenerate token" in response.content.decode()


def test_regenerating_the_token_invalidates_the_old_one(client, ash):
    old = Token.objects.create(user=ash)
    client.force_login(ash)

    response = client.post(reverse("accounts:regenerate_token"))

    assert response.status_code == 302
    new = Token.objects.get(user=ash)
    assert new.key != old.key
    assert APIClient(HTTP_AUTHORIZATION=f"Token {old.key}").get(ENDPOINTS[0]).status_code == 401
    assert APIClient(HTTP_AUTHORIZATION=f"Token {new.key}").get(ENDPOINTS[0]).status_code == 200


def test_regenerating_requires_sign_in_and_a_post(client, ash):
    assert client.post(reverse("accounts:regenerate_token")).status_code == 302  # to sign-in
    assert not Token.objects.exists()
    client.force_login(ash)
    assert client.get(reverse("accounts:regenerate_token")).status_code == 405
