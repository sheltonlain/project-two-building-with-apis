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


class Wish(models.Model):
    """A card variant the user wants. A fulfilled wish keeps its row (crossed out on the
    wishlist) until the user dismisses it."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishes"
    )
    variant = models.ForeignKey(CardVariant, on_delete=models.PROTECT, related_name="wishes")
    notes = models.CharField(max_length=NOTES_MAX_LENGTH, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by = models.ForeignKey(
        OwnedCard, on_delete=models.SET_NULL, null=True, blank=True, related_name="fulfilled_wishes"
    )

    class Meta:
        verbose_name_plural = "wishes"
        constraints = [
            # One active wish per variant; fulfilled wishes don't count.
            models.UniqueConstraint(
                fields=["user", "variant"],
                condition=models.Q(fulfilled_at__isnull=True),
                name="unique_active_wish",
            ),
        ]

    def __str__(self):
        return f"{self.user} wishes for {self.variant}"
