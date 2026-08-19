from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from config.sitemaps import sitemaps
from core.views import health, robots_txt, worker_health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("healthz/", health, name="health"),
    path("healthz/worker/", worker_health, name="worker_health"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path(
        "sitemap.xml", sitemap, {"sitemaps": sitemaps},
        name="sitemap",
    ),
    path("", include("pages.urls")),
    path("", include("taxonomy.urls")),
    path("", include("solutions.urls")),
    path("", include("insights.urls")),
    path("", include("careers.urls")),
    path("", include("people.urls")),
    path("", include("marketing.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
