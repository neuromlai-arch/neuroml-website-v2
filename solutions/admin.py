from django.contrib import admin
from unfold.admin import ModelAdmin

from core.admin import PUBLISH_FIELDSET, SEO_FIELDSET, PublishableAdmin
from solutions.models import OrganizationSolution, Product, Service, UseCase


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
