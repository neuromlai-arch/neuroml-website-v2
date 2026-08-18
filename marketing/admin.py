from django.contrib import admin
from unfold.admin import ModelAdmin

from marketing.models import (
    ClientLogo, ContactSubmission, EngagementModel, NewsletterSubscriber,
    Partner, ProcessStep, Recognition, Testimonial,
)


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ["author_name", "company", "case_study", "featured", "order"]
    list_editable = ["featured", "order"]
    list_filter = ["featured"]
    search_fields = ["author_name", "company", "quote"]
    autocomplete_fields = ["case_study"]


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
class NewsletterSubscriberAdmin(ModelAdmin):
    list_display = ["email", "confirmed", "unsubscribed_at", "created_at"]
    list_filter = ["confirmed"]
    search_fields = ["email"]
    date_hierarchy = "created_at"
