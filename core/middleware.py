from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect

from core.models import Redirect


class RedirectMiddleware:
    """Catches 404s, looks up Redirect, increments hit_count, issues the 301/302.

    Sits after URL resolution has already produced a real 404 — it never
    intercepts a request that resolves successfully.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 404:
            return response

        redirect = (
            Redirect.objects.filter(old_path=request.path).first()
        )
        if redirect is None:
            return response

        Redirect.objects.filter(pk=redirect.pk).update(
            hit_count=redirect.hit_count + 1
        )

        redirect_class = (
            HttpResponsePermanentRedirect if redirect.permanent else HttpResponseRedirect
        )
        return redirect_class(redirect.new_path)
