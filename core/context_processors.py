"""The megamenu builds from real querysets, never hardcoded. Cached so every
page load isn't paying for the joins."""

from django.core.cache import cache
from django.db.models import Prefetch

from marketing.models import Recognition
from pages.models import SiteSettings
from solutions.models import OrganizationSolution, Product, Service
from taxonomy.models import Industry, ServiceCluster

NAV_CACHE_KEY = "megamenu:v1"
NAV_CACHE_TTL = 300
FOOTER_CACHE_KEY = "footer_chrome:v1"
FOOTER_CACHE_TTL = 300
SITE_SETTINGS_CACHE_KEY = "site_settings:v1"
SITE_SETTINGS_CACHE_TTL = 300


def megamenu(request):
    data = cache.get(NAV_CACHE_KEY)
    if data is None:
        data = {
            "nav_clusters": list(
                ServiceCluster.objects.order_by("order").prefetch_related(
                    Prefetch(
                        "services",
                        queryset=Service.objects.live()
                        .filter(show_in_nav=True)
                        .order_by("order"),
                    )
                )
            ),
            "nav_industries": list(
                Industry.objects.filter(show_in_nav=True).order_by("order")
            ),
            "nav_products": list(
                Product.objects.live().filter(show_in_nav=True).order_by("order")
            ),
            "nav_org_solutions": list(
                OrganizationSolution.objects.order_by("org_type", "order")
            ),
        }
        cache.set(NAV_CACHE_KEY, data, NAV_CACHE_TTL)
    return data


def footer_chrome(request):
    recognitions = cache.get(FOOTER_CACHE_KEY)
    if recognitions is None:
        recognitions = list(Recognition.objects.order_by("order"))
        cache.set(FOOTER_CACHE_KEY, recognitions, FOOTER_CACHE_TTL)
    return {"recognitions": recognitions}


def site_settings(request):
    settings_obj = cache.get(SITE_SETTINGS_CACHE_KEY)
    if settings_obj is None:
        settings_obj = SiteSettings.load()
        cache.set(SITE_SETTINGS_CACHE_KEY, settings_obj, SITE_SETTINGS_CACHE_TTL)
    return {"site_settings": settings_obj}
