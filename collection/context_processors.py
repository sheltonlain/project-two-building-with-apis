from . import services


def wish_counts(request):
    """The signed-in user's active wish count, for the nav badge on every page."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"active_wish_count": services.active_wishes(user).count()}
