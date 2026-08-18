from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from core.admin import PUBLISH_FIELDSET, SEO_FIELDSET, PublishableAdmin
from solutions.models import (
    HireRole, OrganizationSolution, Product, Service, Technology, UseCase,
)


@admin.register(Service)
class ServiceAdmin(PublishableAdmin):
    list_display = ["tree_title", "cluster", "state_badge", "show_in_nav", "order"]
    list_editable = ["show_in_nav", "order"]
    list_filter = ["cluster", "status", "show_in_nav", "show_in_form_dropdown"]
    search_fields = ["title", "tagline", "summary"]
    autocomplete_fields = ["parent"]
    fieldsets = [
        (None, {
            "fields": ["cluster", "parent", "title", "slug", "tagline", "summary", "body"],
        }),
        ("Media", {"fields": ["icon", "hero_image"]}),
        ("Navigation", {"fields": ["show_in_nav", "show_in_form_dropdown", "order"]}),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    @admin.display(description="Service")
    def tree_title(self, obj):
        if obj.parent_id:
            return format_html("&nbsp;&nbsp;&nbsp;&nbsp;↳ {}", obj.title)
        return obj.title

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
    list_filter = ["status", "show_in_nav"]
    filter_horizontal = ["industries"]
    search_fields = ["title", "tagline"]
    readonly_fields = ["preview_link", "created_at", "updated_at"]


@admin.register(OrganizationSolution)
class OrganizationSolutionAdmin(ModelAdmin):
    list_display = ["title", "org_type", "order"]
    list_editable = ["order"]
    list_filter = ["org_type"]
    search_fields = ["title"]


def _strip_featured(fieldsets):
    """Technology and HireRole have no `featured` field — strip it from PUBLISH_FIELDSET."""
    return [
        (name, {**opts, "fields": [f for f in opts["fields"] if f != "featured"]})
        if name == "Publishing" else (name, opts)
        for name, opts in fieldsets
    ]


@admin.register(Technology)
class TechnologyAdmin(PublishableAdmin):
    list_display = [
        "name", "service", "state_badge", "show_in_nav", "show_in_stack_grid", "order",
    ]
    list_editable = ["show_in_nav", "show_in_stack_grid", "order"]
    list_filter = ["service", "status", "show_in_nav", "show_in_stack_grid"]
    search_fields = ["name", "tagline"]
    autocomplete_fields = ["service"]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = [
        (None, {"fields": ["service", "name", "slug", "tagline", "logo", "body"]}),
        ("Navigation", {"fields": ["show_in_nav", "show_in_stack_grid", "order"]}),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    def get_fieldsets(self, request, obj=None):
        return _strip_featured(super().get_fieldsets(request, obj))


@admin.register(HireRole)
class HireRoleAdmin(PublishableAdmin):
    list_display = ["title", "starting_rate", "state_badge", "order"]
    list_editable = ["order"]
    list_filter = ["status"]
    search_fields = ["title", "tagline", "summary"]
    filter_horizontal = ["skills", "related_services"]
    fieldsets = [
        (None, {"fields": ["title", "slug", "tagline", "summary", "body"]}),
        ("Hiring", {
            "fields": ["skills", "related_services", "starting_rate", "hero_image", "order"],
        }),
        PUBLISH_FIELDSET,
        SEO_FIELDSET,
    ]
    readonly_fields = ["preview_link", "created_at", "updated_at"]

    def get_fieldsets(self, request, obj=None):
        return _strip_featured(super().get_fieldsets(request, obj))
