"""Query-budget regression tests for the four highest-traffic pages.

Each page's query count is asserted at a fixed number so an accidental N+1
regression (a missing select_related/prefetch_related, or a cache that
stopped being hit) fails CI instead of only showing up as a slow page in
production. Uses seed_demo's data (SVG placeholders, no real images) so
counts are deterministic and don't depend on easy-thumbnails' first-hit
generation cost.

These pages share cached chrome (megamenu, footer, site settings — see
core/context_processors.py — plus a fragment cache around the homepage's
own DB-backed sections and a cached service-dropdown choices list, see
core/signals.py for invalidation). The very first request after a cache
miss is more expensive than these numbers, because it's the one that
populates every cache at once; every request within the TTL window after
that is cheaper, which is what real traffic mostly looks like. So each test
does one warm-up request before asserting the count, matching steady state
rather than the worst case.

If one of these fails after a legitimate change, re-measure with
assertNumQueries(<wrong number>, ...) — Django reports the actual count in
the failure message — and update the number here deliberately, not by
guessing.

Before/after this pass's select_related/caching work (cold-cache counts,
i.e. before any of these pages had ever been requested): homepage 23,
case study list 10, case study detail 18, service detail 9. Warm-cache
counts after that pass: homepage 13, case study list 9, case study detail
10, service detail 8.

Homepage moved to 15 in the frontend polish pass: the stats band added
three COUNT queries (published case studies, live iGaming platforms,
technologies) — real, deliberate, and cheap (COUNT, not a row fetch), not
a regression.

Case study detail moved to 11 in the case-study audit pass: the new
"Explore more" section's related-use-cases lookup is one extra query
(filtered on industry_id, LIMIT 3) — related services and industry reuse
the existing prefetch/select_related, so they're free.
"""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from insights.models import CaseStudy
from solutions.models import Service


class HomepageQueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_homepage_query_count(self):
        url = reverse("home")
        self.client.get(url)
        with self.assertNumQueries(18):
            self.client.get(url)


class CaseStudyListQueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_case_study_list_query_count(self):
        url = reverse("case_study_list")
        self.client.get(url)
        with self.assertNumQueries(9):
            self.client.get(url)


class CaseStudyDetailQueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")
        # seed_demo no longer creates TeamMember rows (see its module
        # docstring), so `author` would otherwise be None here and the
        # template wouldn't issue the extra author lookup this budget
        # expects — set one explicitly so the count stays deterministic
        # regardless of what TeamMember data happens to exist.
        from people.models import TeamMember

        case_study = CaseStudy.objects.live().first()
        case_study.author = TeamMember.objects.create(
            name="Test Author", slug="test-author-perf",
        )
        case_study.save(update_fields=["author"])
        cls.slug = case_study.slug

    def test_case_study_detail_query_count(self):
        url = reverse("case_study_detail", kwargs={"slug": self.slug})
        self.client.get(url)
        with self.assertNumQueries(11):
            self.client.get(url)


class ServiceDetailQueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")
        cls.slug = Service.objects.live().first().slug

    def test_service_detail_query_count(self):
        url = reverse("service_detail", kwargs={"slug": self.slug})
        self.client.get(url)
        with self.assertNumQueries(8):
            self.client.get(url)
