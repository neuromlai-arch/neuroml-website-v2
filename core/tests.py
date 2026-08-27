import shutil
import tempfile
import uuid
from datetime import timedelta
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Redirect
from insights.models import BlogPost, CaseStudy
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


class AttachCaseStudyImagesCommandTests(TestCase):
    """core/management/commands/attach_case_study_images.py — the guard that
    keeps a real client screenshot from ever landing on an anonymised case
    study, and the --include-anonymous escape hatch for generic source
    images that don't identify anyone."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.source = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.source, ignore_errors=True)

    def _write_png(self, directory, filename):
        from pathlib import Path

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")

        target = Path(directory) / filename
        target.write_bytes(buf.getvalue())
        return target

    def _make_case_study(self, slug, **overrides):
        defaults = dict(title=slug.replace("-", " ").title(), slug=slug)
        defaults.update(overrides)
        return CaseStudy.objects.create(**defaults)

    def test_anonymous_case_study_skipped_by_default(self):
        self._make_case_study("clinical-ai-agents", client_anonymous=True)
        self._write_png(self.source, "clinical-ai-agents.png")

        call_command("attach_case_study_images", source=self.source)

        case_study = CaseStudy.objects.get(slug="clinical-ai-agents")
        self.assertFalse(case_study.hero_image)

    def test_include_anonymous_flag_attaches_image(self):
        self._make_case_study("clinical-ai-agents", client_anonymous=True)
        self._write_png(self.source, "clinical-ai-agents.png")

        call_command(
            "attach_case_study_images", source=self.source, include_anonymous=True,
        )

        case_study = CaseStudy.objects.get(slug="clinical-ai-agents")
        self.assertTrue(case_study.hero_image)

    def test_include_anonymous_flag_never_touches_a_named_client(self):
        # The flag lifts the anonymous guard, but a named client's case
        # study never fell under that guard in the first place — it should
        # behave identically with or without the flag.
        self._make_case_study(
            "medical-practice-organic-growth",
            client_anonymous=False, client_name="Carpal Tunnel Pros",
        )
        self._write_png(self.source, "medical-practice-organic-growth.png")

        call_command(
            "attach_case_study_images", source=self.source, include_anonymous=True,
        )

        case_study = CaseStudy.objects.get(slug="medical-practice-organic-growth")
        self.assertTrue(case_study.hero_image)

    def test_include_anonymous_flag_does_not_override_existing_hero_image(self):
        case_study = self._make_case_study("clinical-ai-agents", client_anonymous=True)
        existing = self._write_png(self.source, "existing.png")
        with existing.open("rb") as fh:
            from django.core.files import File

            case_study.hero_image.save("existing.png", File(fh), save=True)

        self._write_png(self.source, "clinical-ai-agents.png")
        call_command(
            "attach_case_study_images", source=self.source, include_anonymous=True,
        )

        case_study.refresh_from_db()
        self.assertIn("existing", case_study.hero_image.name)


class CaseStudyAdminHeroImageUploadTests(TestCase):
    """core/images.py's downscale_in_place() — called from CaseStudy.save()
    on every save, not just via the attach_case_study_images command. The
    admin's add/change view assigns the raw, not-yet-committed
    InMemoryUploadedFile straight to hero_image before instance.save() runs,
    so this exercises a real multipart POST rather than an already-saved
    FieldFile, which is the only way this bug reproduces."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)

        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password",
        )
        self.client.force_login(self.admin_user)

    def _upload(self, width=800, height=600):
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (width, height), color="white").save(buf, format="JPEG")
        return SimpleUploadedFile(
            "hero.jpg", buf.getvalue(), content_type="image/jpeg",
        )

    def _post_data(self, **overrides):
        data = {
            "title": "New Case Study", "slug": "new-case-study",
            "status": CaseStudy.Status.DRAFT,
            "metrics-TOTAL_FORMS": "0", "metrics-INITIAL_FORMS": "0",
            "metrics-MIN_NUM_FORMS": "0", "metrics-MAX_NUM_FORMS": "1000",
            "testimonials-TOTAL_FORMS": "0", "testimonials-INITIAL_FORMS": "0",
            "testimonials-MIN_NUM_FORMS": "0", "testimonials-MAX_NUM_FORMS": "1000",
        }
        data.update(overrides)
        return data

    def test_uploading_a_hero_image_under_the_width_cap_saves_without_error(self):
        # This is the common case — most uploads are already under
        # MAX_ORIGINAL_WIDTH — and the one that previously raised
        # ValueError: I/O operation on closed file.
        response = self.client.post(
            reverse("admin:insights_casestudy_add"),
            data=self._post_data(hero_image=self._upload(width=800, height=600)),
        )
        self.assertEqual(response.status_code, 302, response.content)

        case_study = CaseStudy.objects.get(slug="new-case-study")
        self.assertTrue(case_study.hero_image)

    def test_uploading_a_hero_image_over_the_width_cap_is_downscaled(self):
        response = self.client.post(
            reverse("admin:insights_casestudy_add"),
            data=self._post_data(
                slug="wide-case-study", hero_image=self._upload(width=2000, height=1000),
            ),
        )
        self.assertEqual(response.status_code, 302, response.content)

        case_study = CaseStudy.objects.get(slug="wide-case-study")
        self.assertTrue(case_study.hero_image)
        from PIL import Image

        with case_study.hero_image.open("rb") as fh:
            img = Image.open(fh)
            self.assertLessEqual(img.width, 1600)


class AdminBruteForceProtectionTests(TestCase):
    """django-axes on the admin login (config/settings/base.py):
    AXES_FAILURE_LIMIT=5, AXES_COOLOFF_TIME=30 minutes, keyed on
    username+IP. Uses reverse("admin:login") rather than a hardcoded path —
    the admin was moved from /admin/ to /manage/ but the URL *namespace*
    (set by admin.site.urls itself) is unaffected by where it's mounted."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="axesuser", email="axesuser@example.com", password="a-real-password-123",
        )
        self.login_url = reverse("admin:login")

    def test_fifth_failed_attempt_locks_out_further_attempts(self):
        for _ in range(5):
            response = self.client.post(
                self.login_url, {"username": "axesuser", "password": "wrong"},
            )
        self.assertEqual(response.status_code, 429)

    def test_locked_out_user_is_blocked_even_with_the_correct_password(self):
        for _ in range(5):
            self.client.post(self.login_url, {"username": "axesuser", "password": "wrong"})

        response = self.client.post(
            self.login_url, {"username": "axesuser", "password": "a-real-password-123"},
        )
        self.assertEqual(response.status_code, 429)

    def test_four_failed_attempts_do_not_lock_out(self):
        for _ in range(4):
            response = self.client.post(
                self.login_url, {"username": "axesuser", "password": "wrong"},
            )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self.login_url, {"username": "axesuser", "password": "a-real-password-123"},
        )
        self.assertEqual(response.status_code, 302)

    def test_failed_attempts_are_logged(self):
        with self.assertLogs("axes", level="INFO") as captured:
            self.client.post(self.login_url, {"username": "axesuser", "password": "wrong"})
        self.assertTrue(
            any("login failure" in message.lower() for message in captured.output),
        )
