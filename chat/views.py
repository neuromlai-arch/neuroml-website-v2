"""The grounded chat widget's HTTP surface.

One endpoint (`chat_message`) does everything: rate limiting, retrieval,
grounded generation, and escalation — streamed back as Server-Sent Events so
the widget can render tokens as they arrive. Every guard that can stop a
request from reaching the Anthropic API is checked, in order, before the API
is ever called — a refused/capped/budget-exhausted/rate-limited request
costs nothing.

SSE event types the widget listens for (see static/js/chat-widget.js):
  - `sources` — JSON list of {title, url}, sent once, before any text
  - `text`    — one response text delta per event, JSON-encoded string
  - `done`    — JSON {tokens_used, escalate, calendly_url}
  - `degrade` — JSON {reason}; terminal — no `sources`/`text`/`done` follow.
                The widget swaps its panel to the plain contact form.
"""

import json
from datetime import timedelta

import anthropic
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.utils import timezone
from django_ratelimit.core import is_ratelimited
from django_ratelimit.decorators import ratelimit

from chat.generation import stream_reply
from chat.models import ChatConversation, ChatMessage
from chat.retrieval import retrieve
from core.notifications import notify_staff_of_submission
from marketing.models import ContactSubmission
from pages.models import SiteSettings

MAX_MESSAGES_PER_CONVERSATION = 10
MAX_CONVERSATIONS_PER_IP_PER_DAY = 5
MAX_MESSAGE_LENGTH = 2000

ESCALATION_KEYWORDS = (
    "price", "pricing", "cost", "budget", "quote",
    "timeline", "how long", "how soon", "when can",
    "availability", "available", "start date",
)


def _sse(event, data):
    payload = json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def _degrade_stream(reason):
    yield _sse("degrade", {"reason": reason})


def _get_or_create_conversation(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    conversation = ChatConversation.objects.filter(session_key=session_key).order_by("-started_at").first()
    if conversation is not None:
        return conversation, False

    return conversation, True  # not created yet — caller checks the per-IP cap first


def _should_escalate(conversation, question):
    user_message_count = conversation.messages.filter(role=ChatMessage.Role.USER).count()
    if user_message_count >= 3:
        return True
    lowered = question.lower()
    return any(keyword in lowered for keyword in ESCALATION_KEYWORDS)


def _daily_tokens_used():
    since = timezone.now() - timedelta(hours=24)
    total = ChatMessage.objects.filter(created_at__gte=since).aggregate(total=Sum("tokens_used"))
    return total["total"] or 0


def _maybe_capture_email(conversation, email, transcript_summary, source_url):
    if not email or conversation.visitor_email:
        return
    conversation.visitor_email = email
    conversation.save(update_fields=["visitor_email"])
    submission = ContactSubmission.objects.create(
        first_name="Website visitor",
        email=email,
        message=transcript_summary,
        source=ContactSubmission.Source.CHAT,
        source_url=source_url,
    )
    site_settings = SiteSettings.load()
    notify_staff_of_submission(submission, site_settings=site_settings)


@ratelimit(key="ip", rate="30/h", method="POST", block=False)
def chat_message(request):
    if request.method != "POST" or not settings.ANTHROPIC_API_KEY:
        return HttpResponseBadRequest()

    if getattr(request, "limited", False):
        return StreamingHttpResponse(
            _degrade_stream("Too many messages from this network — please try again in a little while, or use the contact form."),
            content_type="text/event-stream",
        )

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest()

    question = (body.get("message") or "").strip()
    email = (body.get("email") or "").strip()
    if not question or len(question) > MAX_MESSAGE_LENGTH:
        return HttpResponseBadRequest()

    conversation, is_new = _get_or_create_conversation(request)

    if is_new:
        if is_ratelimited(
            request, group="chat-new-conversation", key="ip",
            rate=f"{MAX_CONVERSATIONS_PER_IP_PER_DAY}/d", method="POST", increment=True,
        ):
            return StreamingHttpResponse(
                _degrade_stream("You've reached today's chat limit — please use the contact form instead."),
                content_type="text/event-stream",
            )
        conversation = ChatConversation.objects.create(
            session_key=request.session.session_key,
            source_url=body.get("source_url", "") or request.META.get("HTTP_REFERER", ""),
        )

    if conversation.messages.filter(role=ChatMessage.Role.USER).count() >= MAX_MESSAGES_PER_CONVERSATION:
        return StreamingHttpResponse(
            _degrade_stream("This conversation has reached its message limit — please use the contact form to continue."),
            content_type="text/event-stream",
        )

    if _daily_tokens_used() >= settings.CHAT_DAILY_TOKEN_BUDGET:
        return StreamingHttpResponse(
            _degrade_stream("The chat assistant has reached its usage limit for today — please use the contact form instead."),
            content_type="text/event-stream",
        )

    user_message = ChatMessage.objects.create(
        conversation=conversation, role=ChatMessage.Role.USER, content=question,
    )

    if email:
        transcript = "\n".join(
            f"{m.role}: {m.content}" for m in conversation.messages.order_by("created_at")
        )
        _maybe_capture_email(conversation, email, transcript, conversation.source_url)

    chunks = retrieve(question)
    escalate = _should_escalate(conversation, question)
    if escalate and not conversation.escalated_to_contact:
        conversation.escalated_to_contact = True
        conversation.save(update_fields=["escalated_to_contact"])

    if not chunks:
        return StreamingHttpResponse(
            _no_answer_stream(conversation, escalate),
            content_type="text/event-stream",
        )

    history = [
        {"role": m.role, "content": m.content}
        for m in conversation.messages.exclude(pk=user_message.pk).order_by("created_at")
    ]
    return StreamingHttpResponse(
        _generation_stream(conversation, question, history, chunks, escalate),
        content_type="text/event-stream",
    )


REFUSAL_MESSAGE = (
    "I don't have anything on our site that answers that directly — I'd rather "
    "say so than guess. Use the contact form and a real person will get back to you."
)


def _no_answer_stream(conversation, escalate):
    yield _sse("sources", [])
    yield _sse("text", REFUSAL_MESSAGE)
    ChatMessage.objects.create(
        conversation=conversation, role=ChatMessage.Role.ASSISTANT,
        content=REFUSAL_MESSAGE, cited_sources=[], tokens_used=0,
    )
    yield _sse("done", {
        "tokens_used": 0, "escalate": escalate,
        "calendly_url": SiteSettings.load().calendly_url or None,
    })


def _generation_stream(conversation, question, history, chunks, escalate):
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    full_text = []
    sources = []
    tokens_used = 0
    try:
        for event_type, payload in stream_reply(client, question, history, chunks):
            if event_type == "sources":
                sources = payload
                yield _sse("sources", payload)
            elif event_type == "text":
                full_text.append(payload)
                yield _sse("text", payload)
            elif event_type == "done":
                tokens_used = payload["tokens_used"]
    except Exception:
        message = "Something went wrong on our end — please try again, or use the contact form."
        yield _sse("text", message)
        ChatMessage.objects.create(
            conversation=conversation, role=ChatMessage.Role.ASSISTANT,
            content=message, cited_sources=[], tokens_used=0,
        )
        yield _sse("done", {"tokens_used": 0, "escalate": escalate, "calendly_url": None})
        return

    ChatMessage.objects.create(
        conversation=conversation, role=ChatMessage.Role.ASSISTANT,
        content="".join(full_text), cited_sources=sources, tokens_used=tokens_used,
    )
    yield _sse("done", {
        "tokens_used": tokens_used, "escalate": escalate,
        "calendly_url": SiteSettings.load().calendly_url or None,
    })
