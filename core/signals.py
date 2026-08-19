"""Cache invalidation for the query results cached directly in
core/context_processors.py, the service-dropdown choices cached in
marketing/forms.py, and the homepage's DB-backed template fragment (see
templates/pages/home.html). TTL alone (5 minutes) would eventually
self-heal, but an editor publishing a case study or changing the service
taxonomy shouldn't have to wait for a stale cache to expire — invalidate on
save/delete so the change is live on the next request.
"""

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_delete, post_save

from core.context_processors import (
    FOOTER_CACHE_KEY, NAV_CACHE_KEY, SITE_SETTINGS_CACHE_KEY,
)

HOME_SECTIONS_FRAGMENT = "home_db_sections"


def _invalidate(*keys):
    def handler(sender, **kwargs):
        cache.delete_many(keys)
    return handler


def _invalidate_home_fragment(sender, **kwargs):
    cache.delete(make_template_fragment_key(HOME_SECTIONS_FRAGMENT))


def _invalidate_service_dropdown(sender, **kwargs):
    from marketing.forms import SERVICE_DROPDOWN_CACHE_KEY
    cache.delete(SERVICE_DROPDOWN_CACHE_KEY)


def connect():
    from insights.models import BlogPost, CaseStudy, Handbook
    from marketing.models import (
        ClientLogo, ComparisonRow, ComparisonTable, FAQ, Partner,
        ProcessStep, Recognition, Testimonial,
    )
    from pages.models import SiteSettings
    from solutions.models import (
        OrganizationSolution, Product, Service, ServiceCluster, Technology,
        UseCase,
    )
    from taxonomy.models import Industry

    for model in (Service, ServiceCluster, Product, OrganizationSolution, Industry):
        post_save.connect(_invalidate(NAV_CACHE_KEY), sender=model, weak=False)
        post_delete.connect(_invalidate(NAV_CACHE_KEY), sender=model, weak=False)

    post_save.connect(_invalidate(FOOTER_CACHE_KEY), sender=Recognition, weak=False)
    post_delete.connect(_invalidate(FOOTER_CACHE_KEY), sender=Recognition, weak=False)

    post_save.connect(_invalidate(SITE_SETTINGS_CACHE_KEY), sender=SiteSettings, weak=False)
    post_delete.connect(_invalidate(SITE_SETTINGS_CACHE_KEY), sender=SiteSettings, weak=False)

    post_save.connect(_invalidate_service_dropdown, sender=Service, weak=False)
    post_delete.connect(_invalidate_service_dropdown, sender=Service, weak=False)

    home_models = (
        CaseStudy, Testimonial, ClientLogo, ComparisonTable, ComparisonRow,
        Technology, FAQ, ProcessStep, Partner, UseCase, BlogPost, Handbook,
        Service, ServiceCluster,
    )
    for model in home_models:
        post_save.connect(_invalidate_home_fragment, sender=model, weak=False)
        post_delete.connect(_invalidate_home_fragment, sender=model, weak=False)
