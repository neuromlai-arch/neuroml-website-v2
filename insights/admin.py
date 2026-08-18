from django.contrib import admin
from unfold.admin import StackedInline, TabularInline
from unfold.decorators import display

from core.admin import PUBLISH_FIELDSET, SEO_FIELDSET, PublishableAdmin
from insights.models import BlogPost, CaseStudy, Handbook, Metric, Webinar
from marketing.models import Testimonial


class MetricInline(TabularInline):
    model = Metric
    extra = 2
    fields = ["value", "label", "order"]


class TestimonialInline(StackedInline):
    model = Testimonial
    extra = 0
    fields = ["quote", "author_name", "author_role", "company", "avatar"]


@admin.register(BlogPost)
class BlogPostAdmin(PublishableAdmin):
    list_display = ["title", "author", "state_badge", "published_at", "featured"]
    list_filter = ["status", "featured", "industries", "tags"]
    search_fields = ["title", "excerpt", "body"]
    filter_horizontal = ["industries", "related_services", "tags"]
    autocomplete_fields = ["author"]
    fieldsets = [
        (None, {"fields": ["title", "slug", "excerpt", "hero_image", "hero_alt"]}),
        ("Content", {"fields": ["body"]}),
        ("Classification", {
            "fields": ["author", "industries", "related_services",
                       "tags", "reading_minutes"],
        }),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]


@admin.register(CaseStudy)
class CaseStudyAdmin(PublishableAdmin):
    list_display = [
        "title", "display_client", "industry", "metric_summary",
        "state_badge", "featured",
    ]
    list_filter = ["status", "featured", "industry", "services"]
    search_fields = ["title", "client_name", "challenge", "approach", "outcome"]
    filter_horizontal = ["services", "tags", "tech_stack"]
    autocomplete_fields = ["author"]
    inlines = [MetricInline, TestimonialInline]
    fieldsets = [
        (None, {"fields": ["title", "slug", "excerpt", "hero_image", "hero_alt"]}),
        ("Client", {
            "fields": ["client_name", "client_logo", "client_anonymous", "industry"],
        }),
        ("The story", {
            "fields": ["challenge", "approach", "outcome"],
            "description": "Metrics are added below — they render on this page "
                           "and on the homepage card.",
        }),
        ("Classification", {"fields": ["author", "services", "tech_stack", "tags"]}),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    @display(description="Metrics")
    def metric_summary(self, obj):
        metrics = obj.metrics.all()[:2]
        if not metrics:
            return "None yet"
        return ", ".join(f"{m.value} {m.label}" for m in metrics)


@admin.register(Handbook)
class HandbookAdmin(PublishableAdmin):
    list_display = ["title", "gated", "page_count", "state_badge", "published_at"]
    list_filter = ["status", "gated", "featured"]
    search_fields = ["title", "excerpt"]
    filter_horizontal = ["tags"]
    autocomplete_fields = ["author"]
    readonly_fields = ["preview_link", "created_at", "updated_at"]


@admin.register(Webinar)
class WebinarAdmin(PublishableAdmin):
    list_display = ["title", "starts_at", "availability", "state_badge"]
    list_filter = ["status", "featured"]
    search_fields = ["title", "excerpt"]
    filter_horizontal = ["presenters", "tags"]
    autocomplete_fields = ["author"]
    date_hierarchy = "starts_at"
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    @display(description="Availability")
    def availability(self, obj):
        if obj.is_upcoming:
            return "Upcoming"
        return "On demand" if obj.is_on_demand else "Past — no recording"
