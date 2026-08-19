"""The megamenu builds from real querysets, never hardcoded. Cached so every
page load isn't paying for the joins."""

import json

from django.core.cache import cache
from django.db.models import Prefetch
from django.utils.safestring import mark_safe

from core.calendly import build_calendly_url
from core.utm import utm_initial
from marketing.models import LeadPopup, Recognition
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

    same_as = [
        url for url in (
            settings_obj.linkedin_url, settings_obj.twitter_url,
            settings_obj.facebook_url, settings_obj.youtube_url,
            settings_obj.instagram_url,
        ) if url
    ]
    org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": settings_obj.site_name or "[TODO: company name]",
        "url": request.build_absolute_uri("/"),
    }
    if settings_obj.logo:
        org["logo"] = request.build_absolute_uri(settings_obj.logo.url)
    if settings_obj.email:
        org["email"] = settings_obj.email
    if settings_obj.phone:
        org["telephone"] = settings_obj.phone
    if same_as:
        org["sameAs"] = same_as

    return {
        "site_settings": settings_obj,
        "organization_json_ld": mark_safe(json.dumps(org)),
    }


def lead_popup(request):
    """Not cached like the other chrome — it drives client-side trigger
    logic and its own frequency-cap cookie, so it always needs the live row."""
    from marketing.forms import PopupForm

    popup = LeadPopup.objects.prefetch_related("steps", "badges").first()
    return {"lead_popup": popup, "popup_form": PopupForm()}


def calendly(request):
    """The page-level scheduling URL — UTM-tagged, no prefill (nothing's
    been submitted yet). contact_submit/popup_submit override this same
    context key with a name+email-prefilled version for their success
    states; see marketing/views.py. "" when calendly_url is unset, so
    templates gate on `{% if calendly_url %}` alone."""
    settings_obj = cache.get(SITE_SETTINGS_CACHE_KEY) or SiteSettings.load()
    utm = utm_initial(request)
    return {
        "calendly_url": build_calendly_url(
            settings_obj.calendly_url,
            utm_source=utm["utm_source"], utm_medium=utm["utm_medium"],
            utm_campaign=utm["utm_campaign"],
        ),
    }


def newsletter_form(request):
    """A blank NewsletterForm for the footer signup, present on every page.
    Views that handle the POST (marketing.views.newsletter_signup) render
    their own bound copy instead of using this one."""
    from marketing.forms import NewsletterForm

    return {"newsletter_form": NewsletterForm()}
