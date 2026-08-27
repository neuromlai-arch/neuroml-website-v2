"""Every scheduling entry point (demo page inline widget, case study detail
button, contact/lead-popup success-state button) checks
SiteSettings.calendly_url and renders nothing when it's blank. Calendly's
own ~100KB embed script must never appear in the initial HTML of any page —
it's fetched by static/js/calendly.js only once cookie consent is accepted
(see static/js/cookie-consent.js and tests in this file's TestCase for the
demo page's placeholder-until-accepted behaviour). The demo page loads our
own calendly.js eagerly (via base.html's pre_alpine_scripts block) since its
inline widget needs the calendlyInlineGate Alpine component regardless of
consent state, but that's still just our lazy-loader, never Calendly's own
widget.js."""

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from insights.models import CaseStudy
from pages.models import SiteSettings

CALENDLY_ASSET = "assets.calendly.com/assets/external/widget.js"


class CalendlyEntryPointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")
        call_command("seed_igaming")
        cls.published_slug = CaseStudy.objects.live().first().slug

    def setUp(self):
        cache.clear()

    def _set_calendly_url(self, url):
        settings_obj = SiteSettings.load()
        settings_obj.calendly_url = url
        settings_obj.save()

    # ------------------------------------------------------------- demo page

    def test_demo_page_widget_absent_when_calendly_url_blank(self):
        self._set_calendly_url("")
        response = self.client.get(reverse("demo"))
        self.assertNotContains(response, "calendly-inline-widget")
        self.assertNotContains(response, CALENDLY_ASSET)
        self.assertNotContains(response, "js/calendly.js")

    def test_demo_page_widget_present_when_calendly_url_set(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.get(reverse("demo"))
        self.assertContains(response, "calendly-inline-widget")
        self.assertContains(response, "calendly.com/business-neuroml/30min")
        self.assertContains(response, "js/calendly.js")
        self.assertContains(response, "calendlyInlineGate")
        # The div and our lazy-loader render unconditionally — Calendly's
        # own widget.js only fetches client-side once consent is accepted.
        self.assertNotContains(response, CALENDLY_ASSET)

    def test_demo_page_widget_gated_behind_consent_placeholder(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.get(reverse("demo"))
        self.assertContains(response, "Enable scheduler")

    # ------------------------------------------------------- case study page

    def test_case_study_detail_button_absent_when_calendly_url_blank(self):
        self._set_calendly_url("")
        response = self.client.get(
            reverse("case_study_detail", kwargs={"slug": self.published_slug}),
        )
        self.assertNotContains(response, "Talk to us about work like this")
        self.assertNotContains(response, "js/calendly.js")

    def test_case_study_detail_button_present_when_calendly_url_set(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.get(
            reverse("case_study_detail", kwargs={"slug": self.published_slug}),
        )
        self.assertContains(response, "Talk to us about work like this")
        self.assertContains(response, "openCalendlyPopup")

    # -------------------------------------------------------- contact success

    def test_contact_success_has_no_booking_button_when_calendly_url_blank(self):
        self._set_calendly_url("")
        response = self.client.post(reverse("contact_submit"), {
            "first_name": "Ada", "last_name": "Lovelace",
            "email": "ada@example.com", "message": "Tell me more.", "website": "",
        })
        self.assertContains(response, "Thanks")
        self.assertNotContains(response, "Book a call now")

    def test_contact_success_renders_booking_button_when_calendly_url_set(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.post(reverse("contact_submit"), {
            "first_name": "Ada", "last_name": "Lovelace",
            "email": "ada@example.com", "message": "Tell me more.", "website": "",
        })
        self.assertContains(response, "Book a call now")
        self.assertContains(response, "openCalendlyPopup")

    def test_contact_success_booking_button_prefills_submitted_name_and_email(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.post(reverse("contact_submit"), {
            "first_name": "Ada", "last_name": "Lovelace",
            "email": "ada@example.com", "message": "Tell me more.", "website": "",
        })
        # escapejs encodes '=' and '&' as unicode escapes for safe embedding
        # inside the onclick attribute — check for the pieces that survive
        # escaping rather than the raw query string.
        html = response.content.decode()
        self.assertIn("Ada+Lovelace", html)
        self.assertIn("ada%40example.com", html)

    # ---------------------------------------------------------- popup success

    def test_popup_success_renders_booking_button_when_calendly_url_set(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.post(reverse("popup_submit"), {
            "name": "Grace Hopper", "email": "grace@example.com", "website": "",
        })
        self.assertContains(response, "Book a call now")
        self.assertContains(response, "openCalendlyPopup")

    def test_popup_success_has_no_booking_button_when_calendly_url_blank(self):
        self._set_calendly_url("")
        response = self.client.post(reverse("popup_submit"), {
            "name": "Grace Hopper", "email": "grace@example.com", "website": "",
        })
        self.assertNotContains(response, "Book a call now")

    # --------------------------------------------- script isolation (weight)

    def test_calendly_script_not_loaded_on_homepage(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, CALENDLY_ASSET)
        self.assertNotContains(response, "js/calendly.js")

    def test_calendly_script_not_loaded_on_case_study_index(self):
        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        response = self.client.get(reverse("case_study_list"))
        self.assertNotContains(response, CALENDLY_ASSET)
        self.assertNotContains(response, "js/calendly.js")

    def test_calendly_script_not_loaded_on_service_detail(self):
        from solutions.models import Service

        self._set_calendly_url("https://calendly.com/business-neuroml/30min")
        slug = Service.objects.live().first().slug
        response = self.client.get(reverse("service_detail", kwargs={"slug": slug}))
        self.assertNotContains(response, CALENDLY_ASSET)
        self.assertNotContains(response, "js/calendly.js")

    # --------------------------------------------------------------- admin

    def test_calendly_url_field_in_contact_fieldset(self):
        self.client.force_login(self._staff_user())
        response = self.client.get("/manage/pages/sitesettings/1/change/")
        self.assertContains(response, "calendly_url")

    @staticmethod
    def _staff_user():
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password123",
        )
