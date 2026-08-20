"""The grounded chat widget's own record-keeping. Read-only from the admin
side (see admin.py) — this doubles as lead intelligence, not just a support
log, so nothing here should be editable after the fact.
"""

from django.db import models


class ChatConversation(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    visitor_email = models.EmailField(null=True, blank=True)
    escalated_to_contact = models.BooleanField(default=False)
    source_url = models.CharField(
        max_length=400, blank=True,
        help_text="Page the widget was opened from.",
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Conversation {self.pk} ({self.started_at:%Y-%m-%d %H:%M})"


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Visitor"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages",
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    cited_sources = models.JSONField(
        default=list, blank=True,
        help_text="[{title, url}, ...] the assistant grounded this reply in.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"
