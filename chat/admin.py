from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from chat.models import ChatConversation, ChatMessage


class ChatMessageInline(TabularInline):
    model = ChatMessage
    extra = 0
    fields = ["role", "content", "cited_sources", "tokens_used", "created_at"]
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatConversation)
class ChatConversationAdmin(ModelAdmin):
    """Read-only — this doubles as lead intelligence (what people actually
    ask), so nothing here should be editable after the fact; it only ever
    arrives from the widget."""

    list_display = [
        "id", "started_at", "visitor_email", "escalated_to_contact",
        "message_count", "source_url",
    ]
    list_filter = ["escalated_to_contact", "started_at"]
    search_fields = ["session_key", "visitor_email", "source_url", "messages__content"]
    readonly_fields = [
        "session_key", "started_at", "visitor_email", "escalated_to_contact",
        "source_url",
    ]
    date_hierarchy = "started_at"
    inlines = [ChatMessageInline]

    @admin.display(description="Messages")
    def message_count(self, obj):
        return obj.messages.count()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ChatMessage)
class ChatMessageAdmin(ModelAdmin):
    list_display = ["conversation", "role", "content_preview", "tokens_used", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content", "conversation__session_key", "conversation__visitor_email"]
    readonly_fields = [
        "conversation", "role", "content", "cited_sources", "tokens_used", "created_at",
    ]
    date_hierarchy = "created_at"

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
