"""Health check for the container/load balancer — see Dockerfile — plus
robots.txt, which just needs the sitemap's absolute URL."""

from django.http import HttpResponse
from django.template import loader
from django.urls import reverse

from core.worker_health import get_worker_status


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def worker_health(request):
    """Separate from /healthz/ on purpose — the gunicorn container's own
    liveness must not flip unhealthy just because the *other* qcluster
    process/container died. Point an uptime check at this one instead."""
    status = get_worker_status()
    return HttpResponse(
        status.detail, content_type="text/plain", status=200 if status.healthy else 503,
    )


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    content = loader.render_to_string("robots.txt", {"sitemap_url": sitemap_url})
    return HttpResponse(content, content_type="text/plain")
