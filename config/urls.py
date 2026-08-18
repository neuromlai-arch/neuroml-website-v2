from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("", include("pages.urls")),
    path("", include("taxonomy.urls")),
    path("", include("solutions.urls")),
    path("", include("insights.urls")),
    path("", include("careers.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
