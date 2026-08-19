from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_q.models import OrmQ

from insights.models import Handbook
from marketing.models import ContactSubmission
from pages.models import SiteSettings


def _make_gated_handbook(**overrides):
    defaults = dict(
        title="The AI Readiness Handbook",
        slug="ai-readiness-handbook",
        excerpt="[Placeholder] What to check before you commit budget.",
        gated=True,
        status=Handbook.Status.PUBLISHED,
        published_at=timezone.now(),
    )
    defaults.update(overrides)
    handbook = Handbook.objects.create(**defaults)
    handbook.pdf.save("handbook.pdf", ContentFile(b"%PDF-1.4 fake handbook"), save=True)
    return handbook


class HandbookGateFormViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.handbook = _make_gated_handbook()

    def test_valid_submission_creates_handbook_sourced_submission_and_download_link(self):
        settings_obj = SiteSettings.load()
        settings_obj.email = "team@example.com"
        settings_obj.save()

        response = self.client.post(
            reverse("handbook_gate_submit", args=[self.handbook.slug]),
            {"first_name": "Ada", "email": "ada@example.com", "website": ""},
        )
        self.assertEqual(response.status_code, 200)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.source, ContactSubmission.Source.HANDBOOK)
        self.assertEqual(submission.handbook, self.handbook)
        self.assertContains(response, "download")
        self.assertTrue(OrmQ.objects.exists())

    def test_invalid_submission_saves_nothing(self):
        response = self.client.post(
            reverse("handbook_gate_submit", args=[self.handbook.slug]),
            {"first_name": "", "email": "not-an-email", "website": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "form-error")

    def test_honeypot_triggered_rejects_silently(self):
        self.client.post(
            reverse("handbook_gate_submit", args=[self.handbook.slug]),
            {"first_name": "Bot", "email": "bot@example.com", "website": "gotcha"},
        )
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_rate_limit_blocks_after_threshold(self):
        data = {"first_name": "Ada", "email": "ada@example.com", "website": ""}
        for _ in range(5):
            self.client.post(reverse("handbook_gate_submit", args=[self.handbook.slug]), data)
        ContactSubmission.objects.all().delete()

        response = self.client.post(
            reverse("handbook_gate_submit", args=[self.handbook.slug]), data,
        )

        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "Too many")

    def test_notification_email_renders_without_error(self):
        settings_obj = SiteSettings.load()
        settings_obj.email = "team@example.com"
        settings_obj.save()

        with mock.patch("core.notifications.async_task", side_effect=lambda f, *a: f(*a)):
            self.client.post(
                reverse("handbook_gate_submit", args=[self.handbook.slug]),
                {"first_name": "Ada", "email": "ada@example.com", "website": ""},
            )
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("Handbook download", sent.subject)
        self.assertIn(self.handbook.title, sent.body)

    def test_utm_params_captured_on_submit(self):
        self.client.post(
            reverse("handbook_gate_submit", args=[self.handbook.slug]),
            {
                "first_name": "Ada", "email": "ada@example.com", "website": "",
                "utm_source": "google", "utm_medium": "organic", "utm_campaign": "seo",
            },
        )
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.utm_source, "google")
        self.assertEqual(submission.utm_medium, "organic")
        self.assertEqual(submission.utm_campaign, "seo")
