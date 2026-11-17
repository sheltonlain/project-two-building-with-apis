"""The app's own REST API: the signed-in user's collection entries and wishes. Everything goes
through collection.services, so the API follows the same rules as the website."""

from contextlib import contextmanager

from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from catalog import tcgdex
from collection import services

from .serializers import (
    NewEntrySerializer,
    NewOwnedCardSerializer,
    OwnedCardSerializer,
    OwnedCardUpdateSerializer,
    WishSerializer,
    WishUpdateSerializer,
)


class TCGdexUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "provider_unavailable"


@contextmanager
def card_errors():
    """Turn the errors from saving a card that may not be stored yet into API responses: 400
    for an unknown card or an unsupported variant, 503 when TCGdex can't be reached."""
    try:
        yield
    except tcgdex.NotFound as exc:
        raise ValidationError({"card_id": ["TCGdex has no card with this ID."]}) from exc
    except services.UnsupportedVariant as exc:
        raise ValidationError({"variant": [str(exc)]}) from exc
    except tcgdex.ProviderUnavailable as exc:
        wait = tcgdex.outage_seconds_left() or tcgdex.OUTAGE_SECONDS
        raise TCGdexUnavailable(
            "TCGdex is unavailable right now, and this card isn't stored here yet. "
            f"Try again in about {wait} seconds."
        ) from exc


class EntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """The requesting user's own rows; anyone else's are 404. Lists take `search` (card name or
    notes), `set`, `rarity`, `variant` and `ordering` (a sort key such as `name` or `-price`, as
    on the website)."""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    create_serializer_class = None
    update_serializer_class = None

    def filters(self):
        query = self.request.query_params
        return {
            "search": query.get("search", "").strip(),
            "set_id": query.get("set", "").strip(),
            "rarity": query.get("rarity", "").strip(),
            "variant": query.get("variant", "").strip(),
            "ordering": query.get("ordering", "").strip() or services.DEFAULT_ORDERING,
        }

    def get_serializer_class(self):
        if self.action == "create":
            return self.create_serializer_class
        if self.action == "partial_update":
            return self.update_serializer_class
        return self.serializer_class


class CollectionViewSet(EntryViewSet):
    """Collection entries: one per card variant you own."""

    serializer_class = OwnedCardSerializer
    create_serializer_class = NewOwnedCardSerializer
    update_serializer_class = OwnedCardUpdateSerializer

    def get_queryset(self):
        return services.collection_entries(self.request.user, **self.filters())

    def create(self, request):
        new = self.get_serializer(data=request.data)
        new.is_valid(raise_exception=True)
        with card_errors():
            owned = services.add_copy(
                request.user,
                new.validated_data["card_id"],
                new.validated_data["variant"],
                quantity=new.validated_data["quantity"],
                notes=new.validated_data.get("notes", ""),
            )
        return Response(OwnedCardSerializer(owned).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        changes = self.get_serializer(data=request.data)
        changes.is_valid(raise_exception=True)
        owned = services.update_entry(self.get_object(), **changes.validated_data)
        if owned is None:  # quantity 0 deleted it
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(OwnedCardSerializer(owned).data)

    def perform_destroy(self, owned):
        services.delete_entry(owned)


class WishlistViewSet(EntryViewSet):
    """Wishes: active ones, and fulfilled ones not dismissed yet (their `fulfilled_at` is
    set)."""

    serializer_class = WishSerializer
    create_serializer_class = NewEntrySerializer
    update_serializer_class = WishUpdateSerializer

    def get_queryset(self):
        return services.wish_entries(self.request.user, include_fulfilled=True, **self.filters())

    def create(self, request):
        new = self.get_serializer(data=request.data)
        new.is_valid(raise_exception=True)
        with card_errors():
            wish, created = services.add_wish(
                request.user,
                new.validated_data["card_id"],
                new.validated_data["variant"],
                notes=new.validated_data.get("notes", ""),
            )
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(WishSerializer(wish).data, status=code)

    def partial_update(self, request, pk=None):
        changes = self.get_serializer(data=request.data)
        changes.is_valid(raise_exception=True)
        wish = services.update_wish(self.get_object(), **changes.validated_data)
        return Response(WishSerializer(wish).data)

    def perform_destroy(self, wish):
        services.remove_wish(wish)
