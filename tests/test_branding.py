"""Header/footer/popup logo and favicon wiring: SiteSettings.logo/.logo_dark
override static/brand/*.svg when set, and fall back to it otherwise, per
the branding follow-up task (this repo's model layer isn't touched here —
these are template-only changes)."""

from django.contrib.staticfiles.finders import find
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from pages.models import SiteSettings


class BrandAssetsTests(TestCase):
    """core.context_processors.site_settings caches SiteSettings for 5
    minutes independent of the per-test DB transaction, so each test that
    mutates SiteSettings needs a fresh cache or it'll see a stale object
    left over from whichever test ran first."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        cache.clear()

    def test_static_brand_files_exist(self):
        # django.test.Client doesn't serve STATIC_URL (that's runserver's
        # job in dev, whitenoise's in prod) — check via the staticfiles
        # finder instead, which is what {% static %} itself resolves against.
        for path in (
            "brand/logo.svg", "brand/logo-dark.svg",
            "brand/favicon.svg", "brand/apple-touch-icon.png",
        ):
            with self.subTest(path=path):
                self.assertIsNotNone(find(path), f"static/{path} not found by staticfiles finders")

    def test_apple_touch_icon_linked_in_head(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<link rel="apple-touch-icon" href="/static/brand/apple-touch-icon.png">')

    def test_favicon_falls_back_to_static_file_when_unset(self):
        settings_obj = SiteSettings.load()
        settings_obj.favicon.delete(save=False)
        settings_obj.favicon = None
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<link rel="icon" type="image/svg+xml" href="/static/brand/favicon.svg">')

    def test_favicon_override_wins_when_set(self):
        settings_obj = SiteSettings.load()
        settings_obj.favicon.save("custom-favicon.svg", ContentFile(b"<svg></svg>"), save=True)
        response = self.client.get(reverse("home"))
        self.assertContains(response, settings_obj.favicon.url)
        self.assertNotContains(response, "/static/brand/favicon.svg")

    def test_header_logo_falls_back_to_static_file_when_unset(self):
        settings_obj = SiteSettings.load()
        settings_obj.logo.delete(save=False)
        settings_obj.logo = None
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "/static/brand/logo.svg")

    def test_header_logo_override_wins_when_set(self):
        settings_obj = SiteSettings.load()
        settings_obj.logo.save("custom-logo.svg", ContentFile(b"<svg></svg>"), save=True)
        response = self.client.get(reverse("home"))
        self.assertContains(response, settings_obj.logo.url)

    def test_footer_logo_falls_back_to_static_dark_file_when_unset(self):
        settings_obj = SiteSettings.load()
        settings_obj.logo_dark.delete(save=False)
        settings_obj.logo_dark = None
        settings_obj.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "/static/brand/logo-dark.svg")

    def test_footer_logo_override_wins_when_set(self):
        settings_obj = SiteSettings.load()
        settings_obj.logo_dark.save("custom-logo-dark.svg", ContentFile(b"<svg></svg>"), save=True)
        response = self.client.get(reverse("home"))
        self.assertContains(response, settings_obj.logo_dark.url)

    def test_logo_links_wrap_to_home_with_accessible_name(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        # brand_logo.html always renders an <a href="/" aria-label="..."> —
        # the header, footer, and popup panel each include it at least once.
        self.assertGreaterEqual(html.count('aria-label="[Placeholder] AI Consultancy"'), 3)
