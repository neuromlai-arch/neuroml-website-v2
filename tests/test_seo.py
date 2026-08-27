"""SEO/launch-surface checks: sitemap coverage, robots.txt, JSON-LD
structured data, and absolute canonical/og URLs.

See CLAUDE.md's "SEO — treat as load-bearing" section: this is a rebuild of
an indexed site, so these are load-bearing correctness checks, not nice-to-haves.
"""

import json
import re

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from careers.models import JobPosting
from insights.models import BlogPost, CaseStudy
from solutions.models import Service, UseCase


def _ldjson_blocks(content):
    raw = re.findall(rb'<script type="application/ld\+json">(.*?)</script>', content, re.S)
    return [json.loads(b) for b in raw]


class SitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_sitemap_200(self):
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)

    def test_sitemap_includes_every_live_detail_url(self):
        response = self.client.get(reverse("sitemap"))
        body = response.content.decode()
        for obj in list(Service.objects.live()) + list(UseCase.objects.live()) + list(CaseStudy.objects.live()):
            self.assertIn(obj.get_absolute_url(), body)

    def test_sitemap_excludes_drafts(self):
        draft = Service.objects.live().first()
        draft.status = Service.Status.DRAFT
        draft.save()
        response = self.client.get(reverse("sitemap"))
        self.assertNotIn(draft.get_absolute_url(), response.content.decode())

    def test_sitemap_excludes_noindex(self):
        case_study = CaseStudy.objects.live().first()
        case_study.noindex = True
        case_study.save()
        response = self.client.get(reverse("sitemap"))
        self.assertNotIn(case_study.get_absolute_url(), response.content.decode())


class RobotsTxtTests(TestCase):
    def test_robots_200_and_points_at_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Sitemap:", body)
        self.assertIn(reverse("sitemap"), body)

    def test_robots_disallows_private_paths(self):
        body = self.client.get("/robots.txt").content.decode()
        for path in ("/manage/", "/preview/", "/forms/", "/careers/applications/"):
            self.assertIn(f"Disallow: {path}", body)


class StructuredDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_homepage_organization_jsonld(self):
        response = self.client.get(reverse("home"))
        types = {b.get("@type") for b in _ldjson_blocks(response.content)}
        self.assertIn("Organization", types)

    def test_homepage_faqpage_jsonld(self):
        response = self.client.get(reverse("home"))
        types = {b.get("@type") for b in _ldjson_blocks(response.content)}
        self.assertIn("FAQPage", types)

    def test_case_study_article_jsonld_never_leaks_anonymous_client(self):
        case_study = CaseStudy.objects.live().filter(client_anonymous=True).first()
        self.assertIsNotNone(case_study)
        response = self.client.get(case_study.get_absolute_url())
        blocks = _ldjson_blocks(response.content)
        article = next(b for b in blocks if b.get("@type") == "Article")
        self.assertNotIn(case_study.client_name, json.dumps(article))
        self.assertNotContains(response, case_study.client_name)

    def test_job_posting_jobposting_jsonld(self):
        job = JobPosting.objects.live().first()
        response = self.client.get(job.get_absolute_url())
        types = {b.get("@type") for b in _ldjson_blocks(response.content)}
        self.assertIn("JobPosting", types)

    def test_blog_post_article_jsonld(self):
        post = BlogPost.objects.live().first()
        response = self.client.get(post.get_absolute_url())
        types = {b.get("@type") for b in _ldjson_blocks(response.content)}
        self.assertIn("Article", types)


class AbsoluteUrlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_canonical_and_og_urls_are_absolute(self):
        post = BlogPost.objects.live().first()
        response = self.client.get(post.get_absolute_url())
        html = response.content.decode()
        canonical = re.search(r'<link rel="canonical" href="([^"]+)">', html).group(1)
        og_url = re.search(r'<meta property="og:url" content="([^"]+)">', html).group(1)
        self.assertTrue(canonical.startswith("http"))
        self.assertTrue(og_url.startswith("http"))
        og_image_match = re.search(r'<meta property="og:image" content="([^"]+)">', html)
        if og_image_match:
            self.assertTrue(og_image_match.group(1).startswith("http"))
