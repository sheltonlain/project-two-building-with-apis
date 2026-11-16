from . import services


def wish_counts(request):
    """The signed-in user's active wish count and fulfilled-but-not-dismissed count, for the nav
    badges on every page."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "active_wish_count": services.active_wishes(user).count(),
        "fulfilled_wish_count": services.fulfilled_wishes(user).count(),
    }
