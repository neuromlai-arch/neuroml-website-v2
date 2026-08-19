import uuid
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Redirect
from insights.models import BlogPost
from taxonomy.models import ServiceCluster
from solutions.models import Service


class RedirectMiddlewareTests(TestCase):
    def test_unmatched_404_passes_through_untouched(self):
        response = self.client.get("/this-path-was-never-a-thing/")
        self.assertEqual(response.status_code, 404)

    def test_matching_redirect_returns_301_by_default(self):
        Redirect.objects.create(old_path="/old-page/", new_path="/blog/")
        response = self.client.get("/old-page/")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/blog/")

    def test_permanent_false_returns_302(self):
        Redirect.objects.create(old_path="/temp-page/", new_path="/blog/", permanent=False)
        response = self.client.get("/temp-page/")
        self.assertEqual(response.status_code, 302)

    def test_matching_redirect_increments_hit_count(self):
        redirect = Redirect.objects.create(old_path="/old-page/", new_path="/blog/")
        self.client.get("/old-page/")
        self.client.get("/old-page/")
        redirect.refresh_from_db()
        self.assertEqual(redirect.hit_count, 2)

    def test_a_real_200_response_is_never_intercepted(self):
        # / always resolves — the middleware must not even query Redirect
        # for a request that already succeeded.
        Redirect.objects.create(old_path="/", new_path="/blog/")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class PublishableLiveManagerTests(TestCase):
    """Exercised against Service, but the behaviour under test lives entirely
    in PublishableQuerySet.live() — any Publishable model would do."""

    def setUp(self):
        self.cluster = ServiceCluster.objects.create(name="Agentic AI", slug="agentic-ai")

    def _make(self, title, slug, **overrides):
        defaults = dict(cluster=self.cluster, title=title, slug=slug)
        defaults.update(overrides)
        return Service.objects.create(**defaults)

    def test_draft_never_appears_in_live(self):
        self._make("Draft service", "draft-service", status=Service.Status.DRAFT)
        self.assertEqual(Service.objects.live().count(), 0)

    def test_scheduled_future_publish_never_appears_in_live(self):
        self._make(
            "Future service", "future-service",
            status=Service.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(days=7),
        )
        self.assertEqual(Service.objects.live().count(), 0)

    def test_published_in_the_past_appears_in_live(self):
        self._make(
            "Live service", "live-service",
            status=Service.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(Service.objects.live().count(), 1)

    def test_review_status_never_appears_in_live(self):
        self._make(
            "In review service", "in-review-service",
            status=Service.Status.REVIEW,
            published_at=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(Service.objects.live().count(), 0)

    def test_draft_detail_page_404s_for_anonymous_visitors(self):
        self._make("Draft service", "draft-service", status=Service.Status.DRAFT)
        response = self.client.get(reverse("service_detail", args=["draft-service"]))
        self.assertEqual(response.status_code, 404)

    def test_draft_list_page_never_leaks_a_draft(self):
        self._make("Draft service", "draft-service", status=Service.Status.DRAFT)
        self._make(
            "Live service", "live-service",
            status=Service.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(reverse("service_list"))
        self.assertContains(response, "Live service")
        self.assertNotContains(response, "Draft service")

    def test_draft_blog_post_never_leaks_into_the_public_list(self):
        BlogPost.objects.create(
            title="Unpublished post", slug="unpublished-post",
            status=BlogPost.Status.DRAFT,
        )
        BlogPost.objects.create(
            title="Published post", slug="published-post",
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(reverse("blog_list"))
        self.assertContains(response, "Published post")
        self.assertNotContains(response, "Unpublished post")


class WorkerHealthTests(TestCase):
    """core/worker_health.py — the fix for the queue worker never running
    in production (silent lead loss via django-q2). See DEPLOY.md."""

    def _record_heartbeat(self, *, minutes_ago=0, func="core.tasks.heartbeat"):
        from django_q.models import Success

        stopped = timezone.now() - timedelta(minutes=minutes_ago)
        return Success.objects.create(
            id=uuid.uuid4().hex, name="heartbeat", func=func,
            started=stopped, stopped=stopped, success=True, attempt_count=1,
        )

    def test_heartbeat_schedule_created_by_migration(self):
        from django_q.models import Schedule

        self.assertTrue(
            Schedule.objects.filter(
                func="core.tasks.heartbeat", schedule_type="I", minutes=5,
            ).exists()
        )

    def test_worker_view_503_when_no_heartbeat_ever_recorded(self):
        response = self.client.get(reverse("worker_health"))
        self.assertEqual(response.status_code, 503)

    def test_worker_view_200_when_heartbeat_recent(self):
        self._record_heartbeat(minutes_ago=1)
        response = self.client.get(reverse("worker_health"))
        self.assertEqual(response.status_code, 200)

    def test_worker_view_503_when_heartbeat_stale(self):
        self._record_heartbeat(minutes_ago=30)
        response = self.client.get(reverse("worker_health"))
        self.assertEqual(response.status_code, 503)

    def test_worker_view_ignores_success_rows_for_other_tasks(self):
        # A busy queue on unrelated tasks must not mask a dead heartbeat.
        self._record_heartbeat(minutes_ago=30, func="core.tasks.heartbeat")
        self._record_heartbeat(minutes_ago=0, func="core.notifications._deliver")
        response = self.client.get(reverse("worker_health"))
        self.assertEqual(response.status_code, 503)

    def test_check_worker_health_command_errors_when_unhealthy(self):
        with self.assertRaises(CommandError):
            call_command("check_worker_health")

    def test_check_worker_health_command_succeeds_when_healthy(self):
        self._record_heartbeat(minutes_ago=1)
        out = StringIO()
        call_command("check_worker_health", stdout=out)
        self.assertIn("healthy", out.getvalue())
