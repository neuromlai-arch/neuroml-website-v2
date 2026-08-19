from django.test import TestCase

from pages.admin import SiteSettingsAdmin


class SiteSettingsAdminTests(TestCase):
    def test_recaptcha_site_key_hidden_from_admin_form(self):
        """Removed from fieldsets so an editor can't fill in a value that
        does nothing — see the comment on the model field. Field itself
        stays on the model, reserved for when verification is built."""
        fields = [
            field
            for _, opts in SiteSettingsAdmin.fieldsets
            for field in opts["fields"]
        ]
        self.assertNotIn("recaptcha_site_key", fields)
        self.assertIn("gtm_container_id", fields)
