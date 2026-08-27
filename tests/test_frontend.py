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


class LeadPopupFocusTrapTests(TestCase):
    """The popup's timing rewrite (popup.js) touched only the show/hide
    scheduling — the dialog's accessibility wiring from the earlier build
    (focus trap, Escape-to-close, focus restored to the trigger) lives
    entirely in base.html's x-data attributes and must still be intact."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_popup_dialog_has_focus_trap_escape_and_dialog_semantics(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        self.assertContains(response, 'x-trap.noscroll="open"')
        self.assertContains(response, '@keydown.escape.window="close()"')
        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, 'aria-modal="true"')
        self.assertContains(response, 'aria-labelledby="popup-heading"')
        # x-cloak so a slow Alpine boot never flashes the dialog open before
        # init() has decided whether to arm anything. Search from the
        # popup's own x-data, not the doc start — the mobile menu has an
        # earlier, unrelated x-cloak.
        popup_start = html.find('x-data="leadPopup(')
        self.assertNotEqual(popup_start, -1)
        self.assertIn('x-cloak', html[popup_start:popup_start + 600])


class LeadPopupTimingTests(TestCase):
    """popup.js has no test runner in this repo (playwright is a
    devDependency but nothing wires it up yet) — these are the same kind of
    static-content assertions PopupScriptOrderTests above uses: they can't
    exercise setTimeout/sessionStorage at runtime, but they pin the pieces
    the timing spec depends on so a future edit can't quietly drop one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.popup_js = (Path(settings.BASE_DIR) / "static" / "js" / "popup.js").read_text()

    def test_mobile_skip_happens_before_anything_is_armed(self):
        js = self.popup_js
        mobile_check_pos = js.find("showOnMobile")
        arm_pos = js.find("armInitialTrigger(")
        self.assertNotEqual(mobile_check_pos, -1)
        self.assertNotEqual(arm_pos, -1)
        self.assertLess(
            mobile_check_pos, arm_pos,
            "the show_on_mobile check must return before any trigger is armed, "
            "so mobile skips the JS timer entirely rather than just hiding via CSS",
        )

    def test_submitted_cookie_gates_before_any_scheduling(self):
        js = self.popup_js
        submitted_check_pos = js.find('getCookie("popup_submitted")')
        arm_pos = js.find("armInitialTrigger(")
        self.assertNotEqual(submitted_check_pos, -1)
        self.assertLess(submitted_check_pos, arm_pos)

    def test_cross_session_frequency_cookie_gates_a_fresh_session_only(self):
        js = self.popup_js
        self.assertIn('sessionStorage.getItem(SESSION_ACTIVE_KEY)', js)
        self.assertIn('getCookie("popup_dismissed")', js)
        # The frequency cookie is checked inside the "not already active this
        # session" branch, so a same-session re-show (after a dismissal) is
        # never blocked by it — only a brand new tab session is.
        not_active_pos = js.find("if (!sessionActive)")
        cookie_check_pos = js.find('getCookie("popup_dismissed")')
        session_marker_set_pos = js.find(f'sessionStorage.setItem(SESSION_ACTIVE_KEY, "1")')
        self.assertTrue(not_active_pos < cookie_check_pos < session_marker_set_pos)

    def test_dismiss_count_and_interval_tracked_in_session_storage(self):
        js = self.popup_js
        self.assertIn("DISMISS_COUNT_KEY", js)
        self.assertIn("LAST_DISMISSED_AT_KEY", js)
        self.assertIn("SHORT_INTERVAL_SECONDS = 3 * 60", js)
        self.assertIn("LONG_INTERVAL_SECONDS = 5 * 60", js)
        self.assertIn("SHORT_INTERVAL_DISMISSAL_LIMIT = 2", js)

    def test_dismissal_sets_the_frequency_cookie_using_configured_days(self):
        js = self.popup_js
        self.assertIn('this.setCookie("popup_dismissed", "1", this.config.frequencyDays)', js)

    def test_submission_sets_the_suppression_cookie_using_configured_days(self):
        js = self.popup_js
        self.assertIn('this.setCookie("popup_submitted", "1", this.config.hideAfterSubmitDays)', js)

    def test_timing_logic_has_no_reduced_motion_dependency(self):
        # prefers-reduced-motion is handled sitewide by a single CSS block
        # (see input.css) that neutralises animation/transition durations —
        # popup.js's setTimeout-based scheduling must stay independent of it.
        js = self.popup_js
        self.assertNotIn("matchMedia", js)
        self.assertNotIn("prefers-reduced-motion", js)
