"""Regression guards for JS/CSS wiring that Django's template renderer can't
otherwise catch — these are bugs that only show up when a real browser
executes the page (see the accessibility pass in the launch-readiness task).
"""

from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


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
