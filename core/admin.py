"""Shared admin behaviour: the Publishable base, publish/unpublish actions,
reusable fieldsets, and the Redirect admin."""

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from core.models import Redirect


@admin.action(description="Publish selected")
def publish(modeladmin, request, queryset):
    updated = 0
    for obj in queryset:
        obj.status = obj.Status.PUBLISHED
        if not obj.published_at:
            obj.published_at = timezone.now()
        obj.save()
        updated += 1
    messages.success(request, f"Published {updated} item(s).")


@admin.action(description="Revert to draft")
def unpublish(modeladmin, request, queryset):
    count = queryset.update(status="draft")
    messages.success(request, f"Moved {count} item(s) back to draft.")


class PublishableAdmin(ModelAdmin):
    """Base for anything with the draft/published workflow."""

    actions = [publish, unpublish]
    list_filter = ["status", "published_at"]
    date_hierarchy = "published_at"
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="State")
    def state_badge(self, obj):
        if obj.is_live:
            colour, label = "#15803d", "Live"
        elif obj.status == obj.Status.PUBLISHED:
            colour, label = "#b45309", "Scheduled"
        elif obj.status == obj.Status.REVIEW:
            colour, label = "#1d4ed8", "In review"
        else:
            colour, label = "#6b7280", "Draft"
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>', colour, label,
        )

    @admin.display(description="Preview")
    def preview_link(self, obj):
        if not obj.pk:
            return "—"
        return format_html(
            '<a href="{}?preview=1" target="_blank" rel="noopener">Open preview</a>',
            obj.get_absolute_url(),
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Writers only see their own drafts; editors and admins see everything.
        if request.user.has_perm(f"{self.opts.app_label}.publish_content"):
            return qs
        if request.user.is_superuser:
            return qs
        profile = getattr(request.user, "team_profile", None)
        if profile and hasattr(self.model, "author"):
            return qs.filter(author=profile)
        return qs

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "author") and not obj.author_id:
            obj.author = getattr(request.user, "team_profile", None)
        super().save_model(request, obj, form, change)


SEO_FIELDSET = (
    "Search & social",
    {
        "classes": ["collapse"],
        "fields": [
            "meta_title", "meta_description", "og_image",
            "canonical_url", "noindex",
        ],
    },
)

PUBLISH_FIELDSET = (
    "Publishing",
    {"fields": ["status", "published_at", "featured", "preview_link"]},
)


@admin.register(Redirect)
class RedirectAdmin(ModelAdmin):
    list_display = ["old_path", "new_path", "permanent", "hit_count"]
    list_filter = ["permanent"]
    search_fields = ["old_path", "new_path"]
    readonly_fields = ["hit_count"]
