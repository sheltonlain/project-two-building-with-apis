from io import StringIO

import pytest
import responses
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from collection.management.commands import seed_demo
from collection.models import OwnedCard


@responses.activate  # no URLs registered: any TCGdex request would fail the test
def test_seeding_twice_resets_the_demo_collections_without_calling_tcgdex(db, settings):
    settings.DEBUG = True
    call_command("seed_demo", stdout=StringIO())
    demo = get_user_model().objects.get(username=seed_demo.MAIN_USER)
    OwnedCard.objects.filter(user=demo).first().delete()

    call_command("seed_demo", stdout=StringIO())

    assert OwnedCard.objects.filter(user=demo).count() == len(seed_demo.DEMO_COLLECTION) > 24
    assert demo.check_password(seed_demo.DEMO_PASSWORD)
    assert OwnedCard.objects.filter(user=demo, variant__market_price__isnull=True).exists()
    assert len(responses.calls) == 0


def test_seeding_refuses_to_run_with_debug_off(db, settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_demo")
