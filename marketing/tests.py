from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django_q.models import OrmQ

from marketing.models import ContactSubmission, NewsletterSubscriber
from pages.models import SiteSettings


class ContactFormViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_valid_submission_creates_contact_submission(self):
        response = self.client.post(reverse("contact_submit"), {
            "first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com",
            "message": "Tell me more.", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.source, ContactSubmission.Source.CONTACT)
        self.assertEqual(submission.email, "ada@example.com")

    def test_invalid_submission_renders_errors_and_saves_nothing(self):
        response = self.client.post(reverse("contact_submit"), {
            "first_name": "", "email": "not-an-email", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "form-error")

    def test_honeypot_triggered_rejects_silently(self):
        response = self.client.post(reverse("contact_submit"), {
            "first_name": "Bot", "email": "bot@example.com",
            "message": "buy now", "website": "http://spam.example",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_rate_limit_blocks_after_threshold(self):
        data = {"first_name": "Ada", "email": "ada@example.com", "website": ""}
        for _ in range(5):
            self.client.post(reverse("contact_submit"), data)
        ContactSubmission.objects.all().delete()

        response = self.client.post(reverse("contact_submit"), data)

        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "Too many submissions")

    def test_valid_submission_queues_staff_notification_email(self):
        settings_obj = SiteSettings.load()
        settings_obj.email = "team@example.com"
        settings_obj.save()

        self.client.post(reverse("contact_submit"), {
            "first_name": "Ada", "email": "ada@example.com", "website": "",
        })

        # Delivery happens out-of-process via `manage.py qcluster` — here we
        # only verify the task was actually queued, via the ORM broker.
        self.assertTrue(OrmQ.objects.exists())


class DemoFormViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_valid_submission_creates_demo_sourced_submission(self):
        response = self.client.post(reverse("demo_submit"), {
            "first_name": "Ada", "email": "ada@example.com", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.source, ContactSubmission.Source.DEMO)

    def test_invalid_submission_saves_nothing(self):
        response = self.client.post(reverse("demo_submit"), {
            "first_name": "", "email": "not-an-email", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "form-error")

    def test_honeypot_triggered_rejects_silently(self):
        self.client.post(reverse("demo_submit"), {
            "first_name": "Bot", "email": "bot@example.com", "website": "gotcha",
        })
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_rate_limit_blocks_after_threshold(self):
        data = {"first_name": "Ada", "email": "ada@example.com", "website": ""}
        for _ in range(5):
            self.client.post(reverse("demo_submit"), data)
        ContactSubmission.objects.all().delete()

        response = self.client.post(reverse("demo_submit"), data)

        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "Too many submissions")


class PopupFormViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_valid_submission_creates_popup_sourced_submission(self):
        response = self.client.post(reverse("popup_submit"), {
            "name": "Grace Hopper", "email": "grace@example.com", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.source, ContactSubmission.Source.POPUP)
        self.assertEqual(submission.first_name, "Grace")
        self.assertEqual(submission.last_name, "Hopper")

    def test_invalid_submission_saves_nothing(self):
        response = self.client.post(reverse("popup_submit"), {
            "name": "", "email": "not-an-email", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_honeypot_triggered_rejects_silently(self):
        self.client.post(reverse("popup_submit"), {
            "name": "Bot", "email": "bot@example.com", "website": "gotcha",
        })
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_rate_limit_blocks_after_threshold(self):
        data = {"name": "Grace Hopper", "email": "grace@example.com", "website": ""}
        for _ in range(5):
            self.client.post(reverse("popup_submit"), data)
        ContactSubmission.objects.all().delete()

        response = self.client.post(reverse("popup_submit"), data)

        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(response, "Too many submissions")


class NewsletterFormViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_valid_submission_creates_unconfirmed_subscriber_and_queues_email(self):
        response = self.client.post(reverse("newsletter_signup"), {
            "email": "reader@example.com", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        subscriber = NewsletterSubscriber.objects.get(email="reader@example.com")
        self.assertFalse(subscriber.confirmed)
        self.assertTrue(OrmQ.objects.exists())

    def test_invalid_email_rejected(self):
        response = self.client.post(reverse("newsletter_signup"), {
            "email": "not-an-email", "website": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    def test_already_confirmed_email_rejected(self):
        NewsletterSubscriber.objects.create(email="reader@example.com", confirmed=True)
        response = self.client.post(reverse("newsletter_signup"), {
            "email": "reader@example.com", "website": "",
        })
        self.assertContains(response, "already subscribed")

    def test_honeypot_triggered_rejects_silently(self):
        self.client.post(reverse("newsletter_signup"), {
            "email": "bot@example.com", "website": "gotcha",
        })
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    def test_rate_limit_blocks_after_threshold(self):
        for i in range(3):
            self.client.post(reverse("newsletter_signup"), {
                "email": f"reader{i}@example.com", "website": "",
            })
        response = self.client.post(reverse("newsletter_signup"), {
            "email": "onemore@example.com", "website": "",
        })
        self.assertEqual(NewsletterSubscriber.objects.filter(email="onemore@example.com").count(), 0)
        self.assertContains(response, "Too many attempts")

    def test_confirm_link_marks_subscriber_confirmed(self):
        from django.core import signing

        subscriber = NewsletterSubscriber.objects.create(email="reader@example.com")
        token = signing.dumps({"pk": subscriber.pk}, salt="marketing.newsletter")

        response = self.client.get(reverse("newsletter_confirm", args=[token]))

        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.confirmed)
