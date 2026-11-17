"""Pages that answer HTMX requests with a fragment must never let the browser reuse that fragment
as the full page (for example when the user presses Back after leaving the page)."""

import pytest
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalog import tcgdex

CARDS_URL = f"{tcgdex.BASE_URL}/cards"


@pytest.fixture
def signed_in_client(client, db):
    user = get_user_model().objects.create_user(
        username="ash", email="ash@example.com", password="x"
    )
    client.force_login(user)
    return client


@responses.activate
def test_fragments_and_full_pages_are_cached_separately_and_fragments_not_at_all(
    signed_in_client,
):
    responses.get(f"{tcgdex.BASE_URL}/series", status=503)  # the filter lists; not needed here
    responses.get(CARDS_URL, json=[])
    url = reverse("catalog:search")

    page = signed_in_client.get(url, {"name": "pika"})
    fragment = signed_in_client.get(url, {"name": "pika"}, headers={"HX-Request": "true"})

    for response in (page, fragment):
        assert "HX-Request" in response["Vary"]
    assert "<html" in page.content.decode()
    assert "<html" not in fragment.content.decode()
    assert "no-store" in fragment["Cache-Control"]
    assert "no-store" not in page.get("Cache-Control", "")
