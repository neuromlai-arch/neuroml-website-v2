"""Regression guards for JS/CSS wiring that Django's template renderer can't
otherwise catch — these are bugs that only show up when a real browser
executes the page (see the accessibility pass in the launch-readiness task).
"""

from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from careers.models import JobPosting
from insights.models import BlogPost


class NoLeakedTemplateCommentsTests(TestCase):
    """`{# ... #}` is a single-line-only Django comment — Django's lexer
    requires the closing `#}` on the same line, so a comment written across
    multiple lines isn't parsed as a comment at all and renders as literal
    text (multi-line comments need `{% comment %}...{% endcomment %}`
    instead). Found this live on the homepage and 500.html: an explanatory
    {# #} comment about script ordering was rendering as visible text below
    the footer on every page. Fixed those, and this guards against it
    recurring anywhere a comment like that gets added later."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def _assert_no_raw_comment_markers(self, html):
        # A legitimate single-line {# ... #} never survives to the response;
        # if either delimiter shows up in rendered output, some comment
        # somewhere failed to parse as a comment.
        self.assertNotIn("{#", html)
        self.assertNotIn("#}", html)

    def test_homepage_has_no_leaked_comment_text(self):
        response = self.client.get(reverse("home"))
        self._assert_no_raw_comment_markers(response.content.decode())

    def test_500_page_has_no_leaked_comment_text(self):
        from django.template.loader import render_to_string

        self._assert_no_raw_comment_markers(render_to_string("500.html"))

    def test_blog_detail_has_no_leaked_comment_text(self):
        post = BlogPost.objects.live().first()
        response = self.client.get(post.get_absolute_url())
        self._assert_no_raw_comment_markers(response.content.decode())

    def test_job_posting_detail_has_no_leaked_comment_text(self):
        job = JobPosting.objects.live().first()
        response = self.client.get(job.get_absolute_url())
        self._assert_no_raw_comment_markers(response.content.decode())


class PopupScriptOrderTests(TestCase):
    """popup.js registers an Alpine.data() component on the `alpine:init`
    event. Alpine's CDN build dispatches that event — and starts scanning
    the DOM — the instant its own <script> tag finishes executing. Deferred
    scripts still run in document order, so popup.js's listener has to be
    attached *before* the Alpine core script tag appears, or the popup's
    x-data component fails to register: Alpine can't evaluate `open` on the
    x-show binding, x-cloak has already been stripped, and the popup renders
    permanently visible over every page instead of staying hidden until its
    trigger fires."""

    def test_popup_script_tag_precedes_alpine_core_script_tag(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        popup_pos = html.find("js/popup")
        alpine_pos = html.find("alpinejs@")
        self.assertNotEqual(popup_pos, -1, "popup.js is not included on the homepage")
        self.assertNotEqual(alpine_pos, -1, "Alpine core script is not included on the homepage")
        self.assertLess(
            popup_pos, alpine_pos,
            "popup.js must be loaded before Alpine core, or its alpine:init "
            "listener attaches too late to catch Alpine's boot event",
        )

    def test_popup_js_registers_via_alpine_data_not_a_bare_global(self):
        popup_js = (Path(settings.BASE_DIR) / "static" / "js" / "popup.js").read_text()
        self.assertIn("alpine:init", popup_js)
        self.assertIn("Alpine.data(", popup_js)
        self.assertNotRegex(popup_js, r"^function leadPopup", popup_js)


class MobileMenuFocusTrapTests(TestCase):
    def test_mobile_menu_panel_has_a_focus_trap(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'x-trap.noscroll="mobileOpen"')
