from django.contrib import admin
from unfold.admin import ModelAdmin

from core.admin import SEO_FIELDSET
from pages.models import HomePage, Office, SiteSettings


@admin.register(HomePage)
class HomePageAdmin(ModelAdmin):
    fieldsets = [
        ("Hero", {
            "fields": ["hero_heading", "hero_subheading", "hero_cta_label",
                       "hero_cta_url", "hero_image"],
        }),
        ("Section headings", {
            "fields": ["expertise_heading", "expertise_intro", "use_cases_heading",
                       "case_studies_heading", "insights_heading"],
        }),
        ("Section toggles", {
            "fields": ["show_partners", "show_client_logos", "show_testimonials"],
        }),
        ("Downloads", {"fields": ["capabilities_deck"]}),
        SEO_FIELDSET,
    ]

    def has_add_permission(self, request):
        return not HomePage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = [
        (None, {"fields": ["site_name", "logo", "logo_dark", "favicon", "default_og_image"]}),
        ("Contact", {"fields": ["email", "phone", "whatsapp_number", "whatsapp_prefill", "calendly_url"]}),
        ("Social", {
            "fields": ["linkedin_url", "twitter_url", "facebook_url",
                       "youtube_url", "instagram_url"],
        }),
        # recaptcha_site_key is intentionally left off this form — see the
        # comment on SiteSettings.recaptcha_site_key. Nothing reads it yet,
        # so showing it here would just invite an editor to fill in a value
        # that does nothing.
        ("Tracking", {"fields": ["gtm_container_id"]}),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Office)
class OfficeAdmin(ModelAdmin):
    list_display = ["city", "country", "is_headquarters", "order"]
    list_editable = ["is_headquarters", "order"]
    list_filter = ["is_headquarters", "country"]
    search_fields = ["city", "country", "address"]
