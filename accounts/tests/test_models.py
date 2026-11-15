import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
def test_database_rejects_email_differing_only_in_case():
    User.objects.create_user(username="misty", email="misty@example.com", password="x")

    with pytest.raises(IntegrityError):
        User.objects.create_user(username="ash", email="MISTY@Example.com", password="x")
