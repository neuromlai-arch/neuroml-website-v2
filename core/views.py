"""Health check for the container/load balancer — see Dockerfile — plus
robots.txt, which just needs the sitemap's absolute URL."""

from django.http import HttpResponse
from django.template import loader
from django.urls import reverse


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    content = loader.render_to_string("robots.txt", {"sitemap_url": sitemap_url})
    return HttpResponse(content, content_type="text/plain")
