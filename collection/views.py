from urllib.parse import urlsplit

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from catalog import tcgdex

from . import services


def is_htmx(request):
    return request.headers.get("HX-Request") and not request.headers.get(
        "HX-History-Restore-Request"
    )


PAGE_SIZE = 24
COLLECTION_FILTERS = ("q", "set", "rarity", "variant", "sort")
# (ordering key for services.collection_entries, label), in the order the dropdown shows them.
COLLECTION_SORTS = [
    ("-added", "Newest first"),
    ("added", "Oldest first"),
    ("name", "Name, A–Z"),
    ("-name", "Name, Z–A"),
    ("-price", "Price, high to low"),
    ("price", "Price, low to high"),
    ("-value", "Value, high to low"),
    ("value", "Value, low to high"),
    ("-quantity", "Quantity, most first"),
    ("quantity", "Quantity, fewest first"),
]


RESORT_KEYS = {"quantity", "value"}  # sorts that "+", "−" and Undo can change


def collection_listing(user, query):
    """The filters read from a collection page's query string, and the entries they select."""
    filters = {key: query.get(key, "").strip() for key in COLLECTION_FILTERS}
    if filters["sort"] not in dict(COLLECTION_SORTS):
        filters["sort"] = services.DEFAULT_ORDERING
    entries = services.collection_entries(
        user,
        search=filters["q"],
        set_id=filters["set"],
        rarity=filters["rarity"],
        variant=filters["variant"],
        ordering=filters["sort"],
    )
    return filters, entries


class CollectionView(LoginRequiredMixin, TemplateView):
    """The user's collection, one entry per card variant, from local data only, so it works
    while TCGdex is down."""

    template_name = "collection/collection.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        filters, entries = collection_listing(user, self.request.GET)
        page = Paginator(entries, PAGE_SIZE).get_page(self.request.GET.get("page"))
        context["filters"] = filters
        context["filtered"] = any(filters[key] for key in ("q", "set", "rarity", "variant"))
        context["options"] = services.collection_filter_options(user)
        context["sorts"] = COLLECTION_SORTS
        context["page"] = page
        context["page_range"] = page.paginator.get_elided_page_range(page.number)
        context["has_entries"] = page.paginator.count > 0 or (
            context["filtered"] and services.collection_entries(user).exists()
        )
        context["value"] = services.collection_value(user)
        return context


class ResortWatch:
    """Notices when an entry action moves the entry within the collection page's current sort.

    Only quantity and value sorts can change, so other sorts are never checked. The page's URL
    comes from HTMX's HX-Current-URL header; the re-sort link keeps only its path and query.
    """

    def __init__(self, request, pk):
        self.pk = pk
        self.entries = None
        url = urlsplit(request.headers.get("HX-Current-URL", ""))
        if url.path != reverse("collection:index"):
            return
        filters, entries = collection_listing(request.user, QueryDict(url.query))
        if filters["sort"].removeprefix("-") in RESORT_KEYS:
            self.entries = entries
            self.url = f"{url.path}?{url.query}" if url.query else url.path
            self.before = self.position()

    def position(self):
        pks = list(self.entries.values_list("pk", flat=True))
        return pks.index(self.pk) if self.pk in pks else None

    def moved_url(self):
        """The page's URL if the entry is still listed but in a different place, else None."""
        if self.entries is None or self.before is None:
            return None
        after = self.position()
        return self.url if after is not None and after != self.before else None


UNDO_SESSION_KEY = "collection_undo"
UNDO_KEEP = 20  # most recent removals that can still be undone


class EntryActionView(LoginRequiredMixin, TemplateView):
    """Base for a collection entry's actions. POST only; another user's entry is a 404.

    HTMX requests get the updated entry back (or, if it was deleted, a notice in its place) plus
    the value summary, swapped out of band. Without HTMX the browser goes back to the collection.
    """

    http_method_names = ["post"]
    template_name = "collection/_entry_action.html"
    removes = False  # whether this action removes copies, and so can be undone

    def post(self, request, pk):
        owned = get_object_or_404(services.collection_entries(request.user), pk=pk)
        self.watch = ResortWatch(request, pk)
        label = owned.variant.get_variant_display()
        context = {"pk": pk}
        before = owned.quantity
        try:
            context["notice"] = self.act(owned, label, context)
        except tcgdex.TCGdexError:
            # Only possible if the stored card vanished; the stored card normally makes this local.
            context["error"] = "We couldn't update this card. Reload the page and try again."
        else:
            if self.removes:
                self.remember_removal(pk, before, owned)
                context["undo_url"] = reverse("collection:entry_undo", args=[pk])
        return self.respond(context)

    def remember_removal(self, pk, before, owned):
        """Keep what was removed (and any wish it restored) in the session, so Undo can put it
        back."""
        after = owned.quantity if owned.pk else 0
        record = services.removal_record(
            owned, before - after, getattr(owned, "restored_wish", None)
        )
        records = self.request.session.get(UNDO_SESSION_KEY, {})
        records.pop(str(pk), None)
        records[str(pk)] = record
        self.request.session[UNDO_SESSION_KEY] = dict(list(records.items())[-UNDO_KEEP:])

    def respond(self, context):
        if not is_htmx(self.request):
            return redirect("collection:index")
        user = self.request.user
        if "entry" not in context:
            context["entry"] = services.collection_entries(user).filter(pk=context["pk"]).first()
        context["value"] = services.collection_value(user)
        context["resort_url"] = self.watch.moved_url()
        return self.render_to_response(context)

    def act(self, owned, label, context):
        """Do the action and return the notice to show. May add to `context`."""
        raise NotImplementedError


def add_notice(label, owned):
    """The notice after adding a copy, saying so when it fulfilled a wish."""
    if owned.fulfilled_wish is not None:
        return f"Added 1 {label}. That fulfilled a wish."
    return f"Added 1 {label}."


def remove_notice(label, owned, deleted):
    """The notice after "−", saying so when a wish came back."""
    notice = f"Removed your last {label} copy." if deleted else f"Removed 1 {label}."
    if owned.restored_wish is not None:
        notice += " Its wish is back on your wishlist."
    return notice


class EntryAddView(EntryActionView):
    """The stepper's "+": one more copy of this entry's variant."""

    def act(self, owned, label, context):
        owned = services.add_copy(owned.user, owned.variant.card.tcgdex_id, owned.variant.variant)
        context["wish_fulfilled"] = owned.fulfilled_wish is not None
        return add_notice(label, owned)


class EntryRemoveView(EntryActionView):
    """The stepper's "−": one copy fewer; the entry is deleted when none are left. Restores the
    wish this entry most recently fulfilled."""

    removes = True

    def act(self, owned, label, context):
        deleted = services.remove_copy(owned) is None
        return remove_notice(label, owned, deleted)


class EntryDeleteView(EntryActionView):
    """Remove the whole entry, every copy at once."""

    removes = True

    def act(self, owned, label, context):
        services.delete_entry(owned)
        return f"Removed {owned.variant.card.name} ({label}) from your collection."


class EntryUndoView(EntryActionView):
    """Undo: put back the copies the last "−" or Remove on this entry took away.

    `pk` is the entry's ID before the removal; a deleted entry comes back under a new ID.
    """

    def post(self, request, pk):
        context = {"pk": pk}
        self.watch = ResortWatch(request, pk)
        records = request.session.get(UNDO_SESSION_KEY, {})
        record = records.pop(str(pk), None)
        if record is None:
            context["error"] = "This removal can no longer be undone."
            return self.respond(context)
        request.session[UNDO_SESSION_KEY] = records
        owned = services.undo_removal(request.user, record)
        label = owned.variant.get_variant_display()
        context["entry"] = services.collection_entries(request.user).get(pk=owned.pk)
        context["notice"] = f"Put back {record['removed']} {label}."
        return self.respond(context)


# (ordering key for services.wish_entries, label), in the order the dropdown shows them.
WISHLIST_SORTS = [
    ("-added", "Newest first"),
    ("added", "Oldest first"),
    ("name", "Name, A–Z"),
    ("-name", "Name, Z–A"),
    ("-price", "Price, high to low"),
    ("price", "Price, low to high"),
]


def wishlist_listing(user, query):
    """The wishlist page's context for a query string: its filters, the filtered fulfilled wishes
    (always most recently fulfilled first) and a page of the filtered, sorted active wishes."""
    filters = {key: query.get(key, "").strip() for key in COLLECTION_FILTERS}
    if filters["sort"] not in dict(WISHLIST_SORTS):
        filters["sort"] = services.DEFAULT_ORDERING
    criteria = {
        "search": filters["q"],
        "set_id": filters["set"],
        "rarity": filters["rarity"],
        "variant": filters["variant"],
    }
    wishes = services.wish_entries(user, ordering=filters["sort"], **criteria)
    page = Paginator(wishes, PAGE_SIZE).get_page(query.get("page"))
    return {
        "filters": filters,
        "filtered": any(criteria.values()),
        # What pagination links build on; for an action, the wishlist page's own query string.
        "query": query,
        "fulfilled": services.fulfilled_wish_entries(user, **criteria),
        "page": page,
        "page_range": page.paginator.get_elided_page_range(page.number),
        "has_wishes": services.active_wishes(user).exists()
        or services.fulfilled_wishes(user).exists(),
    }


class WishlistView(LoginRequiredMixin, TemplateView):
    """The user's fulfilled wishes waiting to be dismissed, then their active wishes, newest
    first, with search, filters, sort and pagination. Local data only, so it works while TCGdex
    is down."""

    template_name = "collection/wishlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(wishlist_listing(user, self.request.GET))
        context["options"] = services.wishlist_filter_options(user)
        context["sorts"] = WISHLIST_SORTS
        return context


WISH_UNDO_SESSION_KEY = "wishlist_undo"


class WishActionView(LoginRequiredMixin, TemplateView):
    """Base for a wish's actions. POST only.

    HTMX requests get the wish (or a notice in its place) back, plus the nav's wish count swapped
    out of band. Without HTMX the browser goes back to the wishlist.
    """

    http_method_names = ["post"]
    template_name = "collection/_wish_action.html"

    def respond(self, context):
        if not is_htmx(self.request):
            return redirect("collection:wishlist")
        return self.render_to_response(context)


class WishRemoveView(WishActionView):
    """Remove a wish from the wishlist, with an Undo. Another user's wish is a 404."""

    def post(self, request, pk):
        wish = get_object_or_404(services.active_wishes(request.user), pk=pk)
        record = services.remove_wish(wish)
        records = request.session.get(WISH_UNDO_SESSION_KEY, {})
        records.pop(str(pk), None)
        records[str(pk)] = record
        request.session[WISH_UNDO_SESSION_KEY] = dict(list(records.items())[-UNDO_KEEP:])
        label = wish.variant.get_variant_display()
        return self.respond(
            {
                "pk": pk,
                "notice": f"Removed {wish.variant.card.name} ({label}) from your wishlist.",
                "undo_url": reverse("collection:wish_undo", args=[pk]),
            }
        )


class WishUndoView(WishActionView):
    """Undo: put back the wish that Remove took away.

    `pk` is the wish's ID before the removal; the wish comes back under a new ID.
    """

    def post(self, request, pk):
        records = request.session.get(WISH_UNDO_SESSION_KEY, {})
        record = records.pop(str(pk), None)
        if record is None:
            return self.respond({"pk": pk, "error": "This removal can no longer be undone."})
        request.session[WISH_UNDO_SESSION_KEY] = records
        wish = services.undo_wish_removal(request.user, record)
        return self.respond({"pk": pk, "wish": wish, "notice": "Put it back on your wishlist."})


class WishMoveView(WishActionView):
    """Base for the wish actions that move a wish between the Got it section and the active list
    (Got it, Keep, OK). HTMX requests get the whole wishlist body back, so the wish shows up in
    its new place. The body keeps the page's search, filters, sort and page, read from HTMX's
    HX-Current-URL header.

    `act` returns (wish to show the notice on, or None for a notice above the lists, notice,
    error).
    """

    template_name = "collection/_wishlist_action.html"

    def post(self, request, pk):
        notice_pk, notice, error = self.act(request.user, pk)
        url = urlsplit(request.headers.get("HX-Current-URL", ""))
        query = QueryDict(url.query if url.path == reverse("collection:wishlist") else "")
        context = wishlist_listing(request.user, query)
        context.update({"notice_pk": notice_pk, "notice": notice, "error": error})
        return self.respond(context)

    def act(self, user, pk):
        raise NotImplementedError


class WishGotItView(WishMoveView):
    """Got it: add a copy of an active wish's variant to the collection. That goes through the
    usual add, so it fulfills this wish, which moves to the Got it section."""

    def act(self, user, pk):
        wish = get_object_or_404(services.active_wishes(user), pk=pk)
        variant = wish.variant
        try:
            services.add_copy(user, variant.card.tcgdex_id, variant.variant)
        except tcgdex.TCGdexError:
            # Only possible if the stored card vanished; the stored card normally makes this local.
            return pk, "", "We couldn't add this card. Reload the page and try again."
        return pk, f"Added 1 {variant.get_variant_display()} to your collection.", ""


class WishKeepView(WishMoveView):
    """Keep it on my wishlist: a fulfilled wish moves back into the active list; the copy
    stays."""

    def act(self, user, pk):
        wish = get_object_or_404(services.fulfilled_wishes(user), pk=pk)
        kept = services.keep_wish(wish)
        if kept is None:
            # The user had wished for this variant again; that newer wish is the one that stays.
            kept = services.active_wishes(user).get(variant=wish.variant)
            return kept.pk, "You were already wishing for this again, so this wish stays.", ""
        return kept.pk, "Kept on your wishlist.", ""


class WishDismissView(WishMoveView):
    """OK: delete a fulfilled wish once the user has seen it; the copy stays."""

    def act(self, user, pk):
        wish = get_object_or_404(services.fulfilled_wishes(user), pk=pk)
        services.dismiss_wish(wish)
        label = wish.variant.get_variant_display()
        return None, f"Dismissed {wish.variant.card.name} ({label}).", ""
