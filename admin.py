"""
Admin configuration.

Set up for a small team: three groups (Writer / Editor / Admin), a
draft-preview flow, and inlines so a case study and its metrics are edited
in one place.

Pairs with django-unfold — if you install it, swap the ModelAdmin import
for `from unfold.admin import ModelAdmin` and the inlines for
`unfold.admin.TabularInline`. Everything below works unmodified either way.
"""

from django.contrib import admin, messages
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    BlogPost, CaseStudy, ClientLogo, ContactSubmission, EngagementModel,
    Handbook, HomePage, Industry, Metric, NewsletterSubscriber,
    OrganizationSolution, Partner, ProcessStep, Product, Recognition,
    Redirect, Service, ServiceCluster, Tag, TeamMember, Testimonial,
    UseCase, Webinar,
)


# ---------------------------------------------------------------------------
# shared behaviour
# ---------------------------------------------------------------------------

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


class PublishableAdmin(admin.ModelAdmin):
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


# ---------------------------------------------------------------------------
# taxonomy & people
# ---------------------------------------------------------------------------

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "show_in_nav", "use_case_count"]
    list_editable = ["order", "show_in_nav"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Use cases")
    def use_case_count(self, obj):
        return obj.use_cases.count()


@admin.register(ServiceCluster)
class ServiceClusterAdmin(admin.ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "show_on_about", "order"]
    list_editable = ["show_on_about", "order"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "role"]


# ---------------------------------------------------------------------------
# solutions
# ---------------------------------------------------------------------------

@admin.register(Service)
class ServiceAdmin(PublishableAdmin):
    list_display = ["title", "cluster", "state_badge", "show_in_nav", "order"]
    list_editable = ["show_in_nav", "order"]
    list_filter = ["cluster", "status", "show_in_nav"]
    search_fields = ["title", "tagline", "summary"]
    fieldsets = [
        (None, {"fields": ["cluster", "title", "slug", "tagline", "summary", "body"]}),
        ("Media", {"fields": ["icon", "hero_image"]}),
        ("Navigation", {"fields": ["show_in_nav", "order"]}),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    def get_fieldsets(self, request, obj=None):
        fs = super().get_fieldsets(request, obj)
        # Service has no `featured` field — strip it from the publish block.
        return [
            (name, {**opts, "fields": [f for f in opts["fields"] if f != "featured"]})
            if name == "Publishing" else (name, opts)
            for name, opts in fs
        ]


@admin.register(UseCase)
class UseCaseAdmin(PublishableAdmin):
    list_display = [
        "title", "industry", "related_service", "state_badge",
        "show_on_homepage", "order",
    ]
    list_editable = ["show_on_homepage", "order"]
    list_filter = ["industry", "status", "show_on_homepage"]
    search_fields = ["title", "summary"]
    autocomplete_fields = ["related_service"]
    fieldsets = [
        (None, {"fields": ["industry", "title", "slug", "summary", "body"]}),
        ("Link & placement", {
            "fields": ["related_service", "cta_label", "cta_url",
                       "show_on_homepage", "order"],
        }),
        ("Media", {"fields": ["hero_image"]}),
        ("Publishing", {"fields": ["status", "published_at", "preview_link"]}),
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]


@admin.register(Product)
class ProductAdmin(PublishableAdmin):
    list_display = ["title", "state_badge", "show_in_nav", "order"]
    list_editable = ["show_in_nav", "order"]
    filter_horizontal = ["industries"]
    search_fields = ["title", "tagline"]
    readonly_fields = ["preview_link", "created_at", "updated_at"]


@admin.register(OrganizationSolution)
class OrganizationSolutionAdmin(admin.ModelAdmin):
    list_display = ["title", "org_type", "order"]
    list_editable = ["order"]
    list_filter = ["org_type"]


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------

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


class MetricInline(admin.TabularInline):
    model = Metric
    extra = 2
    fields = ["value", "label", "order"]


class TestimonialInline(admin.StackedInline):
    model = Testimonial
    extra = 0
    fields = ["quote", "author_name", "author_role", "company", "avatar"]


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

    @admin.display(description="Metrics")
    def metric_summary(self, obj):
        metrics = obj.metrics.all()[:2]
        if not metrics:
            return format_html('<span style="color:#b45309">None yet</span>')
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

    @admin.display(description="Availability")
    def availability(self, obj):
        if obj.is_upcoming:
            return "Upcoming"
        return "On demand" if obj.is_on_demand else "Past — no recording"


# ---------------------------------------------------------------------------
# marketing
# ---------------------------------------------------------------------------

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["author_name", "company", "case_study", "featured", "order"]
    list_editable = ["featured", "order"]
    list_filter = ["featured"]
    search_fields = ["author_name", "company", "quote"]
    autocomplete_fields = ["case_study"]


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "active", "order"]
    list_editable = ["active", "order"]


@admin.register(ClientLogo)
class ClientLogoAdmin(admin.ModelAdmin):
    list_display = ["name", "active", "order"]
    list_editable = ["active", "order"]


@admin.register(Recognition)
class RecognitionAdmin(admin.ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ["title", "order"]
    list_editable = ["order"]


@admin.register(EngagementModel)
class EngagementModelAdmin(admin.ModelAdmin):
    list_display = ["title", "order"]
    list_editable = ["order"]


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "company", "source", "handled", "created_at"]
    list_filter = ["source", "handled", "created_at"]
    search_fields = ["email", "first_name", "last_name", "company", "message"]
    readonly_fields = [
        "first_name", "last_name", "email", "phone", "company",
        "message", "source", "source_url", "handbook", "created_at", "updated_at",
    ]
    date_hierarchy = "created_at"

    @admin.display(description="Name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def has_add_permission(self, request):
        return False  # These only arrive from the site forms.


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ["email", "confirmed", "unsubscribed_at", "created_at"]
    list_filter = ["confirmed"]
    search_fields = ["email"]
    date_hierarchy = "created_at"


# ---------------------------------------------------------------------------
# pages & infrastructure
# ---------------------------------------------------------------------------

@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
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


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ["old_path", "new_path", "permanent", "hit_count"]
    list_filter = ["permanent"]
    search_fields = ["old_path", "new_path"]
    readonly_fields = ["hit_count"]


# ---------------------------------------------------------------------------
# roles — run once via a data migration or a management command
# ---------------------------------------------------------------------------

def create_default_groups():
    """Writer: drafts own content. Editor: edits and publishes everything.
    Admin: superuser, no group needed."""

    writer, _ = Group.objects.get_or_create(name="Writer")
    editor, _ = Group.objects.get_or_create(name="Editor")

    content_models = ["blogpost", "casestudy", "handbook", "webinar", "usecase"]

    writer_perms = Permission.objects.filter(
        content_type__model__in=content_models,
        codename__regex=r"^(add|change|view)_",
    )
    writer.permissions.set(writer_perms)

    editor_perms = Permission.objects.filter(
        content_type__model__in=content_models + [
            "service", "product", "testimonial", "metric", "homepage",
            "partner", "clientlogo", "tag", "teammember",
        ],
    )
    editor.permissions.set(editor_perms)

    return writer, editor


admin.site.site_header = "Content admin"
admin.site.site_title = "Content admin"
admin.site.index_title = "Manage site content"
