import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from catalog.models import Card
from collection import services
from collection.tests.helpers import make_owned, make_user, make_wish, select_tags


@pytest.fixture
def ash(db):
    return make_user("ash")


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def names(wishes):
    return [wish.variant.card.name for wish in wishes]


@pytest.mark.parametrize(
    "ordering, expected",
    [
        ("price", ["Pikachu", "Charizard", "Mew"]),  # $0.50, $3.00, no price
        ("-price", ["Charizard", "Pikachu", "Mew"]),
    ],
)
def test_price_sort_puts_wishes_for_unpriced_variants_last_in_both_directions(
    ash, ordering, expected
):
    # Created so that the default newest-first order (Mew, Pikachu, Charizard) matches no case.
    make_wish(ash, "sv03.5-006", "Charizard", price="3.00")
    make_wish(ash, "sv03.5-025", "Pikachu", price="0.50")
    make_wish(ash, "sv03.5-151", "Mew", price=None)

    assert names(services.wish_entries(ash, ordering=ordering)) == expected


def test_filter_options_list_only_values_from_the_users_own_wishes(ash):
    make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    sword = make_wish(ash, "swsh1-001", "Celebi V", "holo", fulfilled_at=timezone.now())
    Card.objects.filter(pk=sword.variant.card.pk).update(
        set_name="Sword & Shield", rarity="Rare Holo V"
    )
    # Owned by Ash but not wished for, and wished for by Misty: neither appears.
    owned = make_owned(ash, "base1-004", "Charizard", "first_edition").variant.card
    Card.objects.filter(pk=owned.pk).update(set_name="Base Set", rarity="Rare Holo")
    mistys = make_wish(make_user("misty"), "neo1-009", "Lugia", "w_promo").variant.card
    Card.objects.filter(pk=mistys.pk).update(set_name="Neo Genesis", rarity="Rare")

    options = services.wishlist_filter_options(ash)

    assert options == {
        "sets": [("sv03.5", "151"), ("swsh1", "Sword & Shield")],
        "rarities": ["Common", "Rare Holo V"],
        "variants": [("reverse", "Reverse holo"), ("holo", "Holo")],
    }


def test_search_and_filters_narrow_active_wishes(ash):
    make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    make_wish(ash, "sv03.5-006", "Charizard", "holo", notes="Trade target for Misty")
    celebi = make_wish(ash, "sv03-001", "Celebi", "holo").variant.card
    Card.objects.filter(pk=celebi.pk).update(rarity="Rare")

    assert names(services.wish_entries(ash, search="PIKA")) == ["Pikachu"]
    assert names(services.wish_entries(ash, search="trade")) == ["Charizard"]
    assert names(services.wish_entries(ash, set_id="sv03")) == ["Celebi"]  # not sv03.5
    assert names(services.wish_entries(ash, rarity="Rare")) == ["Celebi"]
    assert names(services.wish_entries(ash, variant="holo", ordering="name")) == [
        "Celebi",
        "Charizard",
    ]


def test_filters_narrow_fulfilled_wishes_but_sort_never_reorders_them(ash_client, ash):
    now = timezone.now()
    make_wish(ash, "sv03.5-001", "Bulbasaur", fulfilled_at=now - timedelta(days=1))
    make_wish(ash, "sv03.5-151", "Mew", fulfilled_at=now)  # most recently fulfilled
    make_wish(ash, "sv03.5-025", "Pikachu", "reverse", fulfilled_at=now - timedelta(days=2))

    sorted_html = ash_client.get(reverse("collection:wishlist"), {"sort": "name"}).content.decode()
    filtered = ash_client.get(reverse("collection:wishlist"), {"variant": "normal"})

    assert sorted_html.index("Mew") < sorted_html.index("Bulbasaur") < sorted_html.index("Pikachu")
    html = filtered.content.decode()
    assert "Mew" in html and "Bulbasaur" in html and "Pikachu" not in html


def test_pages_hold_24_wishes_and_page_links_keep_the_filters_and_sort(ash_client, ash):
    for number in range(1, 27):
        make_wish(ash, f"sv03.5-{number:03}", f"Card {number:02}", "reverse")
    make_wish(ash, "sv03.5-151", "Mew")  # filtered out by the variant

    query = {"variant": "reverse", "sort": "name", "q": "card"}
    first = ash_client.get(reverse("collection:wishlist"), query)
    second = ash_client.get(reverse("collection:wishlist"), {**query, "page": 2})

    assert len(first.context["page"].object_list) == 24
    assert names(second.context["page"].object_list) == ["Card 25", "Card 26"]
    assert "26 wishes match" in first.content.decode()
    link = re.search(r'href="([^"]*page=2[^"]*)"', first.content.decode()).group(1)
    assert link.startswith(reverse("collection:wishlist") + "?")
    assert "variant=reverse" in link and "sort=name" in link and "q=card" in link


def test_the_page_shows_dropdowns_with_only_my_wished_values_and_says_when_nothing_matches(
    ash_client, ash
):
    make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    make_owned(ash, "sv03.5-006", "Charizard", "holo")

    html = ash_client.get(reverse("collection:wishlist"), {"q": "zzz"}).content.decode()

    assert '<option value="reverse"' in html and '<option value="holo"' not in html
    assert "No wishes match these filters." in html
    assert "Clear filters" in html


def test_got_it_keep_and_ok_keep_the_pages_filters_and_sort(ash_client, ash):
    pikachu = make_wish(ash, "sv03.5-025", "Pikachu", "reverse")
    make_wish(ash, "sv03.5-006", "Charizard")
    page_url = reverse("collection:wishlist") + "?variant=reverse&sort=name"

    response = ash_client.post(
        reverse("collection:wish_got_it", args=[pikachu.pk]),
        headers={"HX-Request": "true", "HX-Current-URL": f"http://testserver{page_url}"},
    )

    html = response.content.decode()
    assert "Pikachu" in html  # now under Got it, still matching the variant filter
    assert "Charizard" not in html  # filtered out, as on the page
    assert response.context["filters"]["sort"] == "name"


def test_set_and_rarity_filters_are_typeable_but_variant_and_sort_stay_plain(ash_client, ash):
    make_wish(ash, "sv03.5-025", "Pikachu")

    html = ash_client.get(reverse("collection:wishlist"), {"rarity": "Common"}).content.decode()

    selects = select_tags(html)
    assert "data-combobox" in selects["set"] and "data-combobox" in selects["rarity"]
    assert "data-combobox" not in selects["variant"] and "data-combobox" not in selects["sort"]
    assert '<option value="Common" selected>Common</option>' in html
