from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_q.models import OrmQ

from careers.models import JobApplication, JobPosting


def _make_job(**overrides):
    defaults = dict(
        title="Senior AI Engineer",
        slug="senior-ai-engineer",
        work_mode=JobPosting.WorkMode.REMOTE,
        employment_type=JobPosting.EmploymentType.FULL_TIME,
        summary="Build agentic systems for enterprise clients.",
        is_open=True,
        status=JobPosting.Status.PUBLISHED,
        published_at=timezone.now(),
        apply_email="hiring@example.com",
    )
    defaults.update(overrides)
    return JobPosting.objects.create(**defaults)


def _resume():
    return SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake resume", content_type="application/pdf")


class JobApplicationSubmitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.job = _make_job()

    def test_valid_submission_creates_application_and_queues_notification(self):
        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {
                "full_name": "Ada Lovelace", "email": "ada@example.com",
                "website": "", "resume": _resume(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 1)
        application = JobApplication.objects.get()
        self.assertEqual(application.job, self.job)
        self.assertTrue(OrmQ.objects.exists())

    def test_invalid_submission_renders_errors_and_saves_nothing(self):
        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {"full_name": "", "email": "not-an-email", "website": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 0)
        self.assertContains(response, "form-error")

    def test_honeypot_triggered_rejects_silently(self):
        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {
                "full_name": "Bot", "email": "bot@example.com",
                "website": "http://spam.example", "resume": _resume(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_rate_limit_blocks_after_threshold(self):
        data = {"full_name": "Ada Lovelace", "email": "ada@example.com", "website": ""}
        for _ in range(5):
            self.client.post(
                reverse("job_application_submit", args=[self.job.slug]),
                {**data, "resume": _resume()},
            )
        JobApplication.objects.all().delete()

        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {**data, "resume": _resume()},
        )

        self.assertEqual(JobApplication.objects.count(), 0)
        self.assertContains(response, "Too many applications")

    def test_notification_email_renders_without_error(self):
        with mock.patch("core.notifications.async_task", side_effect=lambda f, *a: f(*a)):
            self.client.post(
                reverse("job_application_submit", args=[self.job.slug]),
                {
                    "full_name": "Ada Lovelace", "email": "ada@example.com",
                    "website": "", "resume": _resume(),
                },
            )
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("Ada Lovelace", sent.subject)
        self.assertIn(self.job.title, sent.subject)
        self.assertEqual(sent.to, [self.job.apply_email])

    def test_resume_wrong_extension_rejected(self):
        bad_file = SimpleUploadedFile(
            "resume.exe", b"not a resume", content_type="application/octet-stream",
        )
        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {
                "full_name": "Ada Lovelace", "email": "ada@example.com",
                "website": "", "resume": bad_file,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 0)
        self.assertContains(response, "PDF, DOC, or DOCX")

    def test_resume_over_5mb_rejected(self):
        oversized = SimpleUploadedFile(
            "resume.pdf", b"%PDF-1.4 " + b"0" * (5 * 1024 * 1024 + 1),
            content_type="application/pdf",
        )
        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {
                "full_name": "Ada Lovelace", "email": "ada@example.com",
                "website": "", "resume": oversized,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 0)
        self.assertContains(response, "5 MB")

    def test_docx_resume_accepted(self):
        docx_file = SimpleUploadedFile(
            "resume.docx", b"fake docx bytes",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(
            reverse("job_application_submit", args=[self.job.slug]),
            {
                "full_name": "Ada Lovelace", "email": "ada@example.com",
                "website": "", "resume": docx_file,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 1)
