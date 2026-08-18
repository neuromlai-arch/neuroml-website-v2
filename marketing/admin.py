from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from marketing.models import (
    ClientLogo, ComparisonRow, ComparisonTable, ContactSubmission,
    EngagementModel, FAQ, LeadPopup, NewsletterSubscriber, Partner,
    PopupStep, ProcessStep, Recognition, Testimonial,
)


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = [
        "author_name", "company", "source_platform", "rating", "case_study",
        "featured", "order",
    ]
    list_editable = ["featured", "order"]
    list_filter = ["featured", "source_platform"]
    search_fields = ["author_name", "company", "quote"]
    autocomplete_fields = ["case_study"]
    fieldsets = [
        (None, {"fields": ["quote", "author_name", "author_role", "company", "avatar"]}),
        ("Video", {"fields": ["video_url", "video_thumbnail"]}),
        ("Source", {"fields": ["source_platform", "source_url", "rating"]}),
        ("Placement", {"fields": ["case_study", "featured", "order"]}),
    ]


@admin.register(Partner)
class PartnerAdmin(ModelAdmin):
    list_display = ["name", "active", "order"]
    list_editable = ["active", "order"]
    search_fields = ["name"]


@admin.register(ClientLogo)
class ClientLogoAdmin(ModelAdmin):
    list_display = ["name", "active", "order"]
    list_editable = ["active", "order"]
    search_fields = ["name"]


@admin.register(Recognition)
class RecognitionAdmin(ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]
    search_fields = ["name"]


@admin.register(ProcessStep)
class ProcessStepAdmin(ModelAdmin):
    list_display = ["title", "order"]
    list_editable = ["order"]
    search_fields = ["title"]


@admin.register(EngagementModel)
class EngagementModelAdmin(ModelAdmin):
    list_display = ["title", "order"]
    list_editable = ["order"]
    search_fields = ["title"]


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(ModelAdmin):
    list_display = [
        "email", "full_name", "company", "source", "service_interest",
        "budget_range", "is_qualified_badge", "handled", "created_at",
    ]
    list_filter = [
        "source", "project_stage", "budget_range", "handled", "created_at",
    ]
    search_fields = ["email", "first_name", "last_name", "company", "message"]
    readonly_fields = [
        "first_name", "last_name", "email", "phone", "company", "message",
        "source", "source_url", "handbook", "service_interest", "project_stage",
        "budget_range", "utm_source", "utm_medium", "utm_campaign",
        "created_at", "updated_at",
    ]
    date_hierarchy = "created_at"

    @admin.display(description="Name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    @admin.display(description="Qualified", boolean=True)
    def is_qualified_badge(self, obj):
        return obj.is_qualified

    def has_add_permission(self, request):
        return False  # These only arrive from the site forms.


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    list_display = ["email", "confirmed", "unsubscribed_at", "created_at"]
    list_filter = ["confirmed"]
    search_fields = ["email"]
    date_hierarchy = "created_at"


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ["question", "placement", "service", "active", "order"]
    list_editable = ["active", "order"]
    list_filter = ["placement", "active", "service"]
    search_fields = ["question", "answer"]
    autocomplete_fields = ["service"]


class ComparisonRowInline(TabularInline):
    model = ComparisonRow
    extra = 1
    fields = [
        "criterion", "icon", "column_1_value", "column_2_value",
        "column_3_value", "order",
    ]


@admin.register(ComparisonTable)
class ComparisonTableAdmin(ModelAdmin):
    list_display = ["title", "active"]
    list_editable = ["active"]
    search_fields = ["title"]
    inlines = [ComparisonRowInline]


class PopupStepInline(TabularInline):
    model = PopupStep
    extra = 1
    fields = ["text", "order"]


@admin.register(LeadPopup)
class LeadPopupAdmin(ModelAdmin):
    inlines = [PopupStepInline]
    filter_horizontal = ["badges"]
    fieldsets = [
        (None, {
            "fields": ["enabled", "heading", "subheading", "panel_image",
                       "footer_text", "badges"],
        }),
        ("Form", {"fields": ["form_heading", "submit_label", "success_message"]}),
        ("Behaviour", {
            "classes": ["collapse"],
            "fields": [
                "trigger", "delay_seconds", "scroll_percent", "frequency_days",
                "hide_after_submit_days", "show_on_mobile", "exclude_paths",
            ],
        }),
    ]

    def has_add_permission(self, request):
        return not LeadPopup.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
