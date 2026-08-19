"""Real launch copy (see the integration-pass task) landed in seed_demo for
SiteSettings.site_name and the HomePage hero/section headings — everything
else on the homepage stays [Placeholder]/[TODO] pending real content."""

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class HomepageCopyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        cache.clear()

    def test_site_name_is_real(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "NeuroML.ai")

    def test_two_tone_hero_heading_lines(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "AI that ships.")
        self.assertContains(response, "Not AI that demos.")

    def test_hero_body_and_cta(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Most AI pilots never reach production.")
        self.assertContains(response, "Tell us what&#x27;s stuck")

    def test_section_headings(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Three things, done properly")
        self.assertContains(response, "Where this actually gets used")
        self.assertContains(response, "Work that made it to production")
        self.assertContains(response, "Notes from the build")
