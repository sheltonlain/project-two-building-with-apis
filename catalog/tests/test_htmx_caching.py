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
    # (Full pages for signed-in users are no-store too; see the test below.)


def test_signed_in_pages_are_never_reused_from_the_browser_cache(signed_in_client, client):
    """A note added (or a copy added) after a page loaded must still show when the user goes
    Back and then Forward to it, so the browser may not keep its own copy of the page."""
    collection = signed_in_client.get(reverse("collection:index"))

    assert "no-store" in collection["Cache-Control"]


def test_signed_out_pages_keep_ordinary_caching(client, db):
    response = client.get(reverse("home"))

    assert "no-store" not in response.get("Cache-Control", "")
