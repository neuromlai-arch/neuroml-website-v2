"""Render-state edge cases: seed_demo is uniformly populated so it hides
empty/null states that real content will eventually have. Each test here
builds the sparse case directly and checks the page still renders sanely.
"""

from django.test import TestCase
from django.utils import timezone

from insights.models import CaseStudy, Handbook
from marketing.models import Testimonial
from solutions.models import Service, UseCase
from taxonomy.models import Industry, ServiceCluster


class BlankImageFieldTests(TestCase):
    """Every ImageField the task calls out as `blank=True` must render
    without raising when empty, both directly and via {% responsive_img %}."""

    def setUp(self):
        self.cluster = ServiceCluster.objects.create(name="Blank Fields", slug="blank-fields")
        self.industry = Industry.objects.create(name="Blank Industry", slug="blank-industry")

    def test_service_with_no_icon_or_hero_image(self):
        service = Service.objects.create(
            cluster=self.cluster, title="No images", slug="no-images",
            status=Service.Status.PUBLISHED, published_at=timezone.now(),
        )
        response = self.client.get(service.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_case_study_with_no_hero_or_client_logo(self):
        case_study = CaseStudy.objects.create(
            title="No images case study", slug="no-images-case-study",
            status=CaseStudy.Status.PUBLISHED, published_at=timezone.now(),
        )
        response = self.client.get(case_study.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_use_case_with_no_hero_image(self):
        use_case = UseCase.objects.create(
            industry=self.industry, title="No hero use case", slug="no-hero-use-case",
            summary="Summary text.", status=UseCase.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        response = self.client.get(use_case.get_absolute_url())
        self.assertEqual(response.status_code, 200)


class ServiceNavTests(TestCase):
    def test_service_list_and_nav_render_when_most_services_have_no_children(self):
        cluster = ServiceCluster.objects.create(name="Solo Services", slug="solo-services")
        for i in range(3):
            Service.objects.create(
                cluster=cluster, title=f"Childless {i}", slug=f"childless-{i}",
                status=Service.Status.PUBLISHED, published_at=timezone.now(),
            )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/services/")
        self.assertEqual(response.status_code, 200)

    def test_service_detail_with_no_children_omits_children_section(self):
        cluster = ServiceCluster.objects.create(name="Leaf Cluster", slug="leaf-cluster")
        service = Service.objects.create(
            cluster=cluster, title="Leaf Service", slug="leaf-service",
            status=Service.Status.PUBLISHED, published_at=timezone.now(),
        )
        response = self.client.get(service.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Areas within")


class TestimonialEdgeCaseTests(TestCase):
    def test_testimonial_with_no_rating_no_video_no_case_study_renders(self):
        Testimonial.objects.create(
            quote="Great work.", author_name="Jamie Doe", featured=True,
            rating=None, video_url="", case_study=None,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jamie Doe")


class CaseStudyAnonymityTests(TestCase):
    def test_anonymous_client_never_leaks_name_or_logo(self):
        case_study = CaseStudy.objects.create(
            title="Confidential Engagement", slug="confidential-engagement",
            client_name="Definitely Secret Corp", client_anonymous=True,
            status=CaseStudy.Status.PUBLISHED, published_at=timezone.now(),
        )
        response = self.client.get(case_study.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Definitely Secret Corp")
        self.assertContains(response, "Confidential client")

    def test_anonymous_client_logo_never_rendered_even_if_set(self):
        from django.core.files.base import ContentFile

        case_study = CaseStudy.objects.create(
            title="Confidential With Logo", slug="confidential-with-logo",
            client_name="Secret Logo Corp", client_anonymous=True,
            status=CaseStudy.Status.PUBLISHED, published_at=timezone.now(),
        )
        case_study.client_logo.save("logo.svg", ContentFile(b"<svg></svg>"), save=True)
        response = self.client.get(case_study.get_absolute_url())
        self.assertNotContains(response, case_study.client_logo.url)


class HandbookGateTests(TestCase):
    def test_ungated_handbook_never_shows_gate_form(self):
        handbook = Handbook.objects.create(
            title="Open Handbook", slug="open-handbook", gated=False,
            status=Handbook.Status.PUBLISHED, published_at=timezone.now(),
        )
        response = self.client.get(handbook.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Tell us where to send it")


class UseCaseNullRelatedServiceTests(TestCase):
    def test_use_case_with_null_related_service_renders(self):
        industry = Industry.objects.create(name="Null Service Industry", slug="null-service-industry")
        use_case = UseCase.objects.create(
            industry=industry, related_service=None, title="No service use case",
            slug="no-service-use-case", summary="Summary.",
            status=UseCase.Status.PUBLISHED, published_at=timezone.now(),
        )
        response = self.client.get(use_case.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "See the related service")
