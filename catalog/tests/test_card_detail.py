from decimal import Decimal

import pytest
import responses

from catalog import tcgdex

CARDS_URL = f"{tcgdex.BASE_URL}/cards"


def detail(card_id="sv03.5-025", variants=None, tcgplayer=None):
    """A TCGdex card-detail response, trimmed to the fields the app reads."""
    data = {
        "id": card_id,
        "localId": "025",
        "name": "Pikachu",
        "image": "https://assets.tcgdex.net/en/sv/sv03.5/025",
        "rarity": "Common",
        "set": {"id": "sv03.5", "name": "151"},
        "variants": variants or {"normal": True},
    }
    if tcgplayer is not None:
        data["pricing"] = {"cardmarket": None, "tcgplayer": tcgplayer}
    return data


@pytest.mark.django_db
@responses.activate
def test_variants_follow_the_true_flags_in_a_fixed_order():
    flags = {"wPromo": True, "reverse": True, "firstEdition": False, "holo": True, "normal": True}
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail(variants=flags))

    card = tcgdex.card_detail("sv03.5-025")

    assert [(v["code"], v["label"]) for v in card["variants"]] == [
        ("normal", "Normal"),
        ("reverse", "Reverse holo"),
        ("holo", "Holo"),
        ("w_promo", "W Promo"),
    ]


@pytest.mark.django_db
@responses.activate
@pytest.mark.parametrize(
    "flags",
    [
        pytest.param("missing", id="no-variants-key"),
        pytest.param(None, id="variants-null"),
        pytest.param({"normal": False, "reverse": False, "holo": False}, id="all-false"),
    ],
)
def test_a_card_without_any_variant_flag_defaults_to_normal(flags):
    data = detail()
    if flags == "missing":
        del data["variants"]
    else:
        data["variants"] = flags
    responses.get(f"{CARDS_URL}/sv03.5-025", json=data)

    card = tcgdex.card_detail("sv03.5-025")

    assert [v["code"] for v in card["variants"]] == ["normal"]
    assert not tcgdex.cache.get(tcgdex.OUTAGE_KEY)  # not treated as an outage


def market(price):
    return {"productId": 1, "lowPrice": 0.01, "marketPrice": price}


@pytest.mark.django_db
@responses.activate
@pytest.mark.parametrize(
    ("flags", "tcgplayer", "expected"),
    [
        pytest.param(
            {"normal": True, "reverse": True},
            {"unit": "USD", "normal": market(0.28), "reverse-holofoil": market(0.7)},
            {"normal": Decimal("0.28"), "reverse": Decimal("0.70")},
            id="modern-normal-and-reverse",
        ),
        pytest.param(
            {"normal": True, "firstEdition": True},
            {"unit": "USD", "unlimited": market(1.5), "1st-edition": market(12)},
            {"normal": Decimal("1.50"), "first_edition": Decimal("12.00")},
            id="old-set-unlimited-and-1st-edition",
        ),
        pytest.param(
            {"holo": True, "firstEdition": True},
            {
                "unit": "USD",
                "unlimited-holofoil": market(80.1),
                "1st-edition-holofoil": market(400),
            },
            {"holo": Decimal("80.10"), "first_edition": Decimal("400.00")},
            id="old-set-holofoil",
        ),
        pytest.param(
            {"holo": True, "firstEdition": True, "wPromo": True},
            {"unit": "USD", "holofoil": market(987.13)},
            {"holo": Decimal("987.13"), "first_edition": None, "w_promo": None},
            id="variant-without-a-price",
        ),
        pytest.param(
            {"normal": True, "reverse": True},
            {"unit": "USD", "normal": market(None), "reverse-holofoil": {"productId": 1}},
            {"normal": None, "reverse": None},
            id="market-price-null-or-missing",
        ),
        pytest.param({"normal": True}, None, {"normal": None}, id="no-tcgplayer-pricing"),
    ],
)
def test_each_variant_gets_its_tcgplayer_market_price_as_a_decimal(flags, tcgplayer, expected):
    responses.get(f"{CARDS_URL}/sv03.5-025", json=detail(variants=flags, tcgplayer=tcgplayer))

    card = tcgdex.card_detail("sv03.5-025")

    prices = {v["code"]: v["price"] for v in card["variants"]}
    assert prices == expected
    assert all(isinstance(p, Decimal) for p in prices.values() if p is not None)
