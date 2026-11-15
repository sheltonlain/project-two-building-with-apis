import pytest
from django.urls import reverse


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["collection:index", "collection:wishlist", "accounts:account"],
)
def test_anonymous_visitor_is_sent_to_sign_in(client, url_name):
    url = reverse(url_name)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"
