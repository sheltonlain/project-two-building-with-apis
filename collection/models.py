from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalog.models import CardVariant

NOTES_MAX_LENGTH = 500


class OwnedCard(models.Model):
    """How many copies of one card variant a user owns. Deleted when the quantity reaches 0."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_cards"
    )
    variant = models.ForeignKey(CardVariant, on_delete=models.PROTECT, related_name="owned")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    notes = models.CharField(max_length=NOTES_MAX_LENGTH, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "variant"], name="unique_owned_variant"),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="owned_quantity_positive"
            ),
        ]

    def __str__(self):
        return f"{self.user} owns {self.quantity} × {self.variant}"
