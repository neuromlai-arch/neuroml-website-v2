from django.contrib import admin
from unfold.admin import ModelAdmin

from core.admin import SEO_FIELDSET
from pages.models import HomePage


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
