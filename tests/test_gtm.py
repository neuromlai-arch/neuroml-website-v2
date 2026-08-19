"""GTM only renders — head script and body noscript iframe — when
SiteSettings.gtm_container_id is set. Absent by default so no analytics
loads until an editor deliberately opts in via /admin/."""

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

    def test_gtm_head_script_present_when_container_id_set(self):
        settings_obj = SiteSettings.load()
        settings_obj.gtm_container_id = "GTM-TESTID1"
        settings_obj.save()
        response = self.client.get(reverse("home"))
        # The URL itself is assembled client-side (id passed in as an IIFE
        # arg), so check for the loader snippet and the id separately
        # rather than the fully concatenated URL, which never appears
        # verbatim in the rendered HTML.
        self.assertContains(response, "https://www.googletagmanager.com/gtm.js?id=")
        self.assertContains(response, "'GTM-TESTID1'")

    def test_gtm_noscript_iframe_present_when_container_id_set(self):
        settings_obj = SiteSettings.load()
        settings_obj.gtm_container_id = "GTM-TESTID1"
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertContains(
            response,
            "https://www.googletagmanager.com/ns.html?id=GTM-TESTID1",
        )
