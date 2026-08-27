"""GTM is cookie-consent gated (see static/js/cookie-consent.js): the page
only ever stores the container id server-side, in window.GTM_CONTAINER_ID —
loading the actual gtm.js loader happens client-side, and only once the
visitor has accepted the cookie banner. Absent by default so nothing is even
staged until an editor sets gtm_container_id via /manage/.

There's deliberately no <noscript> fallback: a no-JS visitor can't run the
consent banner either, so the compliant default for them is no tracking at
all, not an unconditional tag that bypasses consent entirely."""

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from pages.models import SiteSettings


class GTMTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        cache.clear()

    def test_gtm_absent_when_container_id_blank(self):
        settings_obj = SiteSettings.load()
        settings_obj.gtm_container_id = ""
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "googletagmanager.com")
        self.assertNotContains(response, "GTM_CONTAINER_ID")

    def test_gtm_container_id_staged_when_set(self):
        settings_obj = SiteSettings.load()
        settings_obj.gtm_container_id = "GTM-TESTID1"
        settings_obj.save()
        response = self.client.get(reverse("home"))
        # |escapejs renders the hyphen as a - escape — same string once
        # the browser parses the JS, just not byte-identical in the source.
        self.assertContains(response, 'window.GTM_CONTAINER_ID = "GTM\\u002DTESTID1"')

    def test_gtm_loader_never_renders_server_side_even_when_container_id_set(self):
        """The actual gtm.js loader snippet lives only in cookie-consent.js
        and only runs client-side after consent — it must never appear in
        the server-rendered page, consented or not, since the server has no
        way to know the visitor's choice."""
        settings_obj = SiteSettings.load()
        settings_obj.gtm_container_id = "GTM-TESTID1"
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "https://www.googletagmanager.com/gtm.js?id=")

    def test_gtm_noscript_iframe_never_renders(self):
        settings_obj = SiteSettings.load()
        settings_obj.gtm_container_id = "GTM-TESTID1"
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "googletagmanager.com/ns.html")
