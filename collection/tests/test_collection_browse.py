import pytest
from django.urls import reverse

from catalog.models import Card
from collection import services
from collection.tests.helpers import make_owned, make_user, select_tags


@pytest.fixture
def ash(db):
    return make_user("ash")


def names(entries):
    return [entry.variant.card.name for entry in entries]


def test_search_matches_card_names_and_notes_ignoring_case(ash):
    make_owned(ash, "sv03.5-025", "Pikachu")
    trade = make_owned(ash, "sv03.5-006", "Charizard")
    trade.notes = "Trade target for Misty"
    trade.save()
    make_owned(ash, "sv03.5-001", "Bulbasaur")

    assert names(services.collection_entries(ash, search="PIKA")) == ["Pikachu"]
    assert names(services.collection_entries(ash, search="trade")) == ["Charizard"]


@pytest.mark.parametrize(
    "ordering, expected",
    [
        ("price", ["Pikachu", "Charizard", "Mew"]),  # $0.50, $3.00, no price
        ("-price", ["Charizard", "Pikachu", "Mew"]),
        ("value", ["Charizard", "Pikachu", "Mew"]),  # $3.00, $5.00 (10 × $0.50), no price
        ("-value", ["Pikachu", "Charizard", "Mew"]),
    ],
)
def test_price_and_value_sorts_put_unpriced_entries_last_in_both_directions(
    ash, ordering, expected
):
    # Created so that the default newest-first order (Mew, Pikachu, Charizard) matches no case.
    make_owned(ash, "sv03.5-006", "Charizard", price="3.00")
    make_owned(ash, "sv03.5-025", "Pikachu", price="0.50", quantity=10)
    make_owned(ash, "sv03.5-151", "Mew", price=None, quantity=5)

    assert names(services.collection_entries(ash, ordering=ordering)) == expected


def test_filter_options_list_only_values_from_the_users_own_collection(ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "reverse")
    make_owned(ash, "sv03.5-006", "Charizard", "holo")
    sword = make_owned(ash, "swsh1-001", "Celebi V", "holo").variant.card
    Card.objects.filter(pk=sword.pk).update(set_name="Sword & Shield", rarity="Rare Holo V")
    mistys = make_owned(make_user("misty"), "base1-002", "Blastoise", "first_edition").variant.card
    Card.objects.filter(pk=mistys.pk).update(set_name="Base Set", rarity="Rare Holo")

    options = services.collection_filter_options(ash)

    assert options == {
        "sets": [("sv03.5", "151"), ("swsh1", "Sword & Shield")],
        "rarities": ["Common", "Rare Holo V"],
        "variants": [("reverse", "Reverse holo"), ("holo", "Holo")],
    }


def test_set_rarity_and_variant_filters_are_exact_matches(ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "reverse")
    make_owned(ash, "sv03.5-006", "Charizard", "holo")
    celebi = make_owned(ash, "sv03-001", "Celebi", "holo").variant.card
    Card.objects.filter(pk=celebi.pk).update(rarity="Rare")

    assert names(services.collection_entries(ash, set_id="sv03")) == ["Celebi"]  # not sv03.5
    assert names(services.collection_entries(ash, rarity="Rare")) == ["Celebi"]
    assert names(services.collection_entries(ash, variant="holo")) == ["Celebi", "Charizard"]
    assert names(services.collection_entries(ash, set_id="sv03.5", variant="holo")) == ["Charizard"]


def test_an_unknown_sort_key_falls_back_to_newest_first(ash):
    make_owned(ash, "sv03.5-006", "Charizard")
    make_owned(ash, "sv03.5-025", "Pikachu")

    assert names(services.collection_entries(ash, ordering="-bogus")) == ["Pikachu", "Charizard"]


@pytest.fixture
def ash_client(client, ash):
    client.force_login(ash)
    return client


def test_the_page_holds_24_entries_and_page_links_keep_the_filters_and_sort(ash_client, ash):
    for number in range(1, 27):
        make_owned(ash, f"sv03.5-{number:03}", f"Card {number:02}", price="1.00")
    make_owned(ash, "sv03.5-151", "Mew")  # filtered out by the search below

    response = ash_client.get(reverse("collection:index"), {"q": "card", "sort": "name"})

    page = response.context["page"]
    html = response.content.decode()
    assert page.paginator.count == 26 and len(page.object_list) == 24
    assert names(page.object_list)[:2] == ["Card 01", "Card 02"]
    assert "26 entries match" in html
    assert 'href="?q=card&amp;sort=name&amp;page=2"' in html
    second = ash_client.get(reverse("collection:index"), {"q": "card", "sort": "name", "page": 2})
    assert names(second.context["page"].object_list) == ["Card 25", "Card 26"]


def test_the_filter_form_keeps_the_choices_and_offers_only_the_users_values(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu", "reverse")
    make_owned(make_user("misty"), "base1-002", "Blastoise", "first_edition")

    html = ash_client.get(
        reverse("collection:index"), {"variant": "reverse", "sort": "-value"}
    ).content.decode()

    assert '<option value="reverse" selected>Reverse holo</option>' in html
    assert '<option value="-value" selected>' in html
    assert "first_edition" not in html and "base1" not in html


def test_no_matches_says_so_without_calling_the_collection_empty(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu")

    html = ash_client.get(reverse("collection:index"), {"q": "zzz"}).content.decode()

    assert "No entries match these filters" in html
    assert "Your collection is empty" not in html


def step(client, action, entry, page_url):
    return client.post(
        reverse(f"collection:{action}", args=[entry.pk]),
        HTTP_HX_REQUEST="true",
        HTTP_HX_CURRENT_URL=f"http://testserver{page_url}",
    ).content.decode()


def test_a_step_that_moves_an_entry_in_a_quantity_sort_offers_a_re_sort(ash_client, ash):
    make_owned(ash, "sv03.5-006", "Charizard", quantity=3)
    pikachu = make_owned(ash, "sv03.5-025", "Pikachu", quantity=1)
    page_url = reverse("collection:index") + "?q=a&sort=-quantity"

    still_below = step(ash_client, "entry_add", pikachu, page_url)  # 2 vs 3: order unchanged
    assert "Re-sort" not in still_below
    moved = step(ash_client, "entry_add", pikachu, page_url)  # 3 vs 3: the newer Pikachu leads

    assert 'id="resort-prompt"' in moved and 'hx-swap-oob="true"' in moved
    assert 'href="/collection/?q=a&amp;sort=-quantity"' in moved
    assert "3 owned" in moved  # the entry itself is still swapped in place


def test_steps_never_offer_a_re_sort_when_the_sort_ignores_quantity(ash_client, ash):
    make_owned(ash, "sv03.5-006", "Charizard", quantity=2)
    pikachu = make_owned(ash, "sv03.5-025", "Pikachu", quantity=1)

    html = step(ash_client, "entry_add", pikachu, reverse("collection:index") + "?sort=name")
    html += step(ash_client, "entry_add", pikachu, reverse("collection:index") + "?sort=name")

    assert "Re-sort" not in html


def test_set_and_rarity_filters_are_typeable_but_variant_and_sort_stay_plain(ash_client, ash):
    make_owned(ash, "sv03.5-025", "Pikachu")

    html = ash_client.get(reverse("collection:index"), {"set": "sv03.5"}).content.decode()

    selects = select_tags(html)
    assert "data-combobox" in selects["set"] and "data-combobox" in selects["rarity"]
    assert "data-combobox" not in selects["variant"] and "data-combobox" not in selects["sort"]
    assert '<option value="sv03.5" selected>151</option>' in html  # the real select still submits
