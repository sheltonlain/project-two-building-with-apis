from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from catalog import tcgdex

from . import services


def is_htmx(request):
    return request.headers.get("HX-Request") and not request.headers.get(
        "HX-History-Restore-Request"
    )


class CollectionView(LoginRequiredMixin, TemplateView):
    """The user's collection, one entry per card variant, from local data only, so it works
    while TCGdex is down."""

    template_name = "collection/collection.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = services.collection_entries(self.request.user)
        context["value"] = services.collection_value(self.request.user)
        return context


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
        label = owned.variant.get_variant_display()
        context = {"pk": pk}
        before = services.removal_record(owned, owned.quantity)
        try:
            context["notice"] = self.act(owned, label)
        except tcgdex.TCGdexError:
            # Only possible if the stored card vanished; the stored card normally makes this local.
            context["error"] = "We couldn't update this card. Reload the page and try again."
        else:
            if self.removes:
                self.remember_removal(pk, before, owned)
                context["undo_url"] = reverse("collection:entry_undo", args=[pk])
        return self.respond(context)

    def remember_removal(self, pk, before, owned):
        """Keep what was removed in the session, so Undo can put it back."""
        after = owned.quantity if owned.pk else 0
        before["removed"] -= after
        records = self.request.session.get(UNDO_SESSION_KEY, {})
        records.pop(str(pk), None)
        records[str(pk)] = before
        self.request.session[UNDO_SESSION_KEY] = dict(list(records.items())[-UNDO_KEEP:])

    def respond(self, context):
        if not is_htmx(self.request):
            return redirect("collection:index")
        user = self.request.user
        if "entry" not in context:
            context["entry"] = services.collection_entries(user).filter(pk=context["pk"]).first()
        context["value"] = services.collection_value(user)
        return self.render_to_response(context)

    def act(self, owned, label):
        raise NotImplementedError


class EntryAddView(EntryActionView):
    """The stepper's "+": one more copy of this entry's variant."""

    def act(self, owned, label):
        services.add_copy(owned.user, owned.variant.card.tcgdex_id, owned.variant.variant)
        return f"Added 1 {label}."


class EntryRemoveView(EntryActionView):
    """The stepper's "−": one copy fewer; the entry is deleted when none are left."""

    removes = True

    def act(self, owned, label):
        if services.remove_copy(owned) is None:
            return f"Removed your last {label} copy."
        return f"Removed 1 {label}."


class EntryDeleteView(EntryActionView):
    """Remove the whole entry, every copy at once."""

    removes = True

    def act(self, owned, label):
        services.delete_entry(owned)
        return f"Removed {owned.variant.card.name} ({label}) from your collection."


class EntryUndoView(EntryActionView):
    """Undo: put back the copies the last "−" or Remove on this entry took away.

    `pk` is the entry's ID before the removal; a deleted entry comes back under a new ID.
    """

    def post(self, request, pk):
        context = {"pk": pk}
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


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "collection/wishlist.html"
