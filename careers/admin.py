from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from careers.models import JobApplication, JobPosting
from careers.views import make_resume_token
from core.admin import PUBLISH_FIELDSET, SEO_FIELDSET, PublishableAdmin


@admin.register(JobPosting)
class JobPostingAdmin(PublishableAdmin):
    list_display = [
        "title", "department", "location", "work_mode", "employment_type",
        "is_open", "state_badge",
    ]
    list_editable = ["is_open"]
    list_filter = ["status", "department", "work_mode", "employment_type", "is_open"]
    search_fields = ["title", "department", "location", "summary"]
    fieldsets = [
        (None, {
            "fields": ["title", "slug", "department", "location", "work_mode",
                       "employment_type", "experience_min_years",
                       "experience_max_years", "summary"],
        }),
        ("Details", {
            "fields": ["responsibilities", "requirements", "nice_to_have", "benefits"],
        }),
        ("Applications", {"fields": ["is_open", "apply_email"]}),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    def get_fieldsets(self, request, obj=None):
        fs = super().get_fieldsets(request, obj)
        # JobPosting has no `featured` field — strip it from the publish block.
        return [
            (name, {**opts, "fields": [f for f in opts["fields"] if f != "featured"]})
            if name == "Publishing" else (name, opts)
            for name, opts in fs
        ]


@admin.register(JobApplication)
class JobApplicationAdmin(ModelAdmin):
    list_display = ["full_name", "job", "email", "stage", "created_at"]
    list_filter = ["stage", "job"]
    search_fields = ["full_name", "email", "job__title"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "job", "full_name", "email", "phone", "portfolio_url", "cover_note",
        "resume_link", "created_at", "updated_at",
    ]
    fieldsets = [
        (None, {
            "fields": ["job", "full_name", "email", "phone", "portfolio_url", "cover_note"],
        }),
        ("Resume", {"fields": ["resume_link"]}),
        ("Pipeline", {"fields": ["stage", "notes"]}),
    ]

    @admin.display(description="Resume")
    def resume_link(self, obj):
        if not obj.resume:
            return "—"
        token = make_resume_token(obj)
        url = reverse("resume_download", args=[token])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Download resume</a>', url,
        )

    def has_add_permission(self, request):
        return False  # These only arrive from the site's application form.
