"""Renders every named URL in the project against real seed_demo data.

Nothing here had ever been rendered before this test existed — the goal is
to catch template/view bugs that only show up with real objects (blank
images, empty relations, null FKs), not to re-assert business logic already
covered by each app's own tests.py.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.template.loader import render_to_string
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from careers.models import JobApplication, JobPosting
from careers.views import make_resume_token
from insights.models import BlogPost, CaseStudy, Handbook, Webinar
from insights.views import HANDBOOK_SALT
from marketing.models import LeadPopup
from pages.views import make_preview_token
from people.models import TeamMember
from solutions.models import HireRole, Product, Service, Technology, UseCase
from taxonomy.models import Industry, ServiceCluster

User = get_user_model()


class SeedDataMixin:
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")


# Named URLs that take no arguments and are always a plain GET -> 200.
SIMPLE_GET_URLS = [
    "health", "robots_txt", "sitemap",
    "home", "about", "contact", "privacy", "terms", "demo",
    "industry_list", "service_list", "product_list", "technology_list",
    "hire_role_list", "blog_list", "case_study_list", "handbook_list",
    "webinar_list", "job_posting_list", "use_case_list",
    "contact_submit", "demo_submit", "popup_submit", "newsletter_signup",
]


class SimpleURLTests(SeedDataMixin, TestCase):
    def test_simple_urls_return_200(self):
        for name in SIMPLE_GET_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)


class DetailURLTests(SeedDataMixin, TestCase):
    """Each detail route, hit with the first real live object of its model."""

    def _first_live(self, manager):
        obj = manager.live().first()
        self.assertIsNotNone(obj, f"seed_demo produced no live object for {manager.model}")
        return obj

    def test_industry_detail(self):
        industry = Industry.objects.first()
        self.assertIsNotNone(industry)
        response = self.client.get(reverse("industry_detail", args=[industry.slug]))
        self.assertEqual(response.status_code, 200)

    def test_service_detail(self):
        service = self._first_live(Service.objects)
        response = self.client.get(reverse("service_detail", args=[service.slug]))
        self.assertEqual(response.status_code, 200)

    def test_use_case_detail(self):
        use_case = self._first_live(UseCase.objects)
        response = self.client.get(reverse("use_case_detail", args=[use_case.slug]))
        self.assertEqual(response.status_code, 200)

    def test_product_detail(self):
        product = self._first_live(Product.objects)
        response = self.client.get(reverse("product_detail", args=[product.slug]))
        self.assertEqual(response.status_code, 200)

    def test_technology_detail(self):
        technology = self._first_live(Technology.objects)
        response = self.client.get(reverse("technology_detail", args=[technology.slug]))
        self.assertEqual(response.status_code, 200)

    def test_hire_role_detail(self):
        role = self._first_live(HireRole.objects)
        response = self.client.get(reverse("hire_role_detail", args=[role.slug]))
        self.assertEqual(response.status_code, 200)

    def test_blog_detail(self):
        post = self._first_live(BlogPost.objects)
        response = self.client.get(reverse("blog_detail", args=[post.slug]))
        self.assertEqual(response.status_code, 200)

    def test_case_study_detail(self):
        case_study = self._first_live(CaseStudy.objects)
        response = self.client.get(reverse("case_study_detail", args=[case_study.slug]))
        self.assertEqual(response.status_code, 200)

    def test_handbook_detail_gated_and_ungated(self):
        for handbook in Handbook.objects.live():
            with self.subTest(gated=handbook.gated):
                response = self.client.get(reverse("handbook_detail", args=[handbook.slug]))
                self.assertEqual(response.status_code, 200)

    def test_webinar_detail(self):
        webinar = self._first_live(Webinar.objects)
        response = self.client.get(reverse("webinar_detail", args=[webinar.slug]))
        self.assertEqual(response.status_code, 200)

    def test_job_posting_detail(self):
        job = self._first_live(JobPosting.objects)
        response = self.client.get(reverse("job_posting_detail", args=[job.slug]))
        self.assertEqual(response.status_code, 200)

    def test_team_member_detail(self):
        member = TeamMember.objects.filter(show_on_about=True).first()
        self.assertIsNotNone(member)
        response = self.client.get(reverse("team_member_detail", args=[member.slug]))
        self.assertEqual(response.status_code, 200)

    def test_home_industry_panel(self):
        industry = Industry.objects.first()
        response = self.client.get(reverse("home_industry_panel", args=[industry.slug]))
        self.assertEqual(response.status_code, 200)


class GatedFormURLTests(SeedDataMixin, TestCase):
    """Form endpoints that need an extra slug/token in the URL."""

    def test_handbook_gate_submit_get(self):
        handbook = Handbook.objects.live().filter(gated=True).first()
        self.assertIsNotNone(handbook)
        response = self.client.get(reverse("handbook_gate_submit", args=[handbook.slug]))
        self.assertEqual(response.status_code, 200)

    def test_job_application_submit_get(self):
        job = JobPosting.objects.live().filter(is_open=True).first()
        self.assertIsNotNone(job)
        response = self.client.get(reverse("job_application_submit", args=[job.slug]))
        self.assertEqual(response.status_code, 200)

    def test_handbook_download_valid_token(self):
        handbook = Handbook.objects.live().filter(gated=True).first()
        token = signing.dumps({"pk": handbook.pk}, salt=HANDBOOK_SALT)
        response = self.client.get(reverse("handbook_download", args=[token]))
        self.assertEqual(response.status_code, 200)

    def test_newsletter_confirm_valid_token(self):
        from marketing.models import NewsletterSubscriber

        subscriber = NewsletterSubscriber.objects.create(email="smoke@example.com")
        token = signing.dumps({"pk": subscriber.pk}, salt="marketing.newsletter")
        response = self.client.get(reverse("newsletter_confirm", args=[token]))
        self.assertEqual(response.status_code, 200)

    def test_resume_download_valid_token_staff_only(self):
        job = JobPosting.objects.live().first()
        application = JobApplication.objects.create(
            job=job, full_name="Ada Lovelace", email="ada@example.com",
        )
        application.resume.save("resume.pdf", ContentFile(b"%PDF-1.4 fake"), save=True)
        token = make_resume_token(application)

        anon_response = self.client.get(reverse("resume_download", args=[token]))
        self.assertEqual(anon_response.status_code, 403)

        staff = User.objects.create_user("staffer", password="pw", is_staff=True)
        staff_client = Client()
        staff_client.force_login(staff)
        response = staff_client.get(reverse("resume_download", args=[token]))
        self.assertEqual(response.status_code, 200)


class PreviewViewTests(SeedDataMixin, TestCase):
    """A valid token on an unpublished object 200s for staff; anything else 404s."""

    def setUp(self):
        cluster = ServiceCluster.objects.first()
        self.draft_service = Service.objects.create(
            cluster=cluster, title="Draft-only service", slug="draft-only-service",
            status=Service.Status.DRAFT,
        )
        self.staff = User.objects.create_user("previewer", password="pw", is_staff=True)

    def test_valid_token_on_unpublished_object_returns_200_for_staff(self):
        token = make_preview_token(self.draft_service)
        client = Client()
        client.force_login(self.staff)
        response = client.get(reverse("content_preview", args=[token]), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_valid_token_rejected_for_anonymous_visitors(self):
        token = make_preview_token(self.draft_service)
        response = self.client.get(reverse("content_preview", args=[token]))
        self.assertEqual(response.status_code, 403)

    def test_invalid_token_404s(self):
        client = Client()
        client.force_login(self.staff)
        response = client.get(reverse("content_preview", args=["not-a-real-token"]))
        self.assertEqual(response.status_code, 404)

    def test_expired_token_404s(self):
        token = make_preview_token(self.draft_service)
        client = Client()
        client.force_login(self.staff)
        future = timezone.now().timestamp() + (60 * 60 * 24) + 3600
        with mock.patch("django.core.signing.time.time", return_value=future):
            response = client.get(reverse("content_preview", args=[token]))
        self.assertEqual(response.status_code, 404)


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ErrorPageTests(TestCase):
    def test_404_page_renders(self):
        response = self.client.get("/this-url-definitely-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page not found", status_code=404)

    def test_500_template_renders_standalone(self):
        # 500.html deliberately doesn't extend base.html (see its own comment)
        # so it can't depend on context processors that might be the very
        # thing that failed. Render it directly rather than manufacturing a
        # real unhandled exception through the test client.
        html = render_to_string("500.html")
        self.assertIn("Something went wrong", html)


class HomepageLeadPopupTests(SeedDataMixin, TestCase):
    def test_homepage_renders_with_lead_popup_enabled(self):
        popup = LeadPopup.load()
        popup.enabled = True
        popup.save()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "popup-heading")

    def test_homepage_renders_with_lead_popup_disabled(self):
        popup = LeadPopup.load()
        popup.enabled = False
        popup.save()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "popup-heading")


class URLTemplateCoverageTests(SeedDataMixin, TestCase):
    """Part 1's two reporting lists, enforced so they can't silently drift."""

    def test_every_public_model_has_a_detail_url(self):
        # Every public content model must have a get_absolute_url-backed
        # detail route, which the DetailURLTests above already exercise.
        for model in (
            Service, Product, Technology, HireRole, BlogPost, CaseStudy,
            Handbook, Webinar, JobPosting, TeamMember, Industry, UseCase,
        ):
            self.assertTrue(hasattr(model, "get_absolute_url"), model)
