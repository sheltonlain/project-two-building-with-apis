from django.utils.cache import add_never_cache_headers, patch_vary_headers


class HtmxVaryMiddleware:
    """Stop the browser from showing an HTMX fragment as a whole page.

    Several pages answer the same URL with a fragment for HTMX requests and a full page otherwise.
    Without this, pressing Back to a URL that HTMX pushed into history can show the cached
    fragment (no layout or styles). `Vary` keeps the two apart in the cache, and fragments are
    never stored at all.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        patch_vary_headers(response, ["HX-Request", "HX-History-Restore-Request"])
        if request.headers.get("HX-Request"):
            add_never_cache_headers(response)
        return response
