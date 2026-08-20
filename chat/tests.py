import json

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from chat.models import ChatConversation, ChatMessage
from chat.retrieval import retrieve
from insights.models import CaseStudy
from solutions.models import Service
from taxonomy.models import ServiceCluster


def _sse_events(response):
    """Parses a StreamingHttpResponse's SSE body into [(event, data), ...]."""
    body = b"".join(response.streaming_content).decode()
    events = []
    for frame in body.split("\n\n"):
        if not frame.strip():
            continue
        event, data = "message", ""
        for line in frame.split("\n"):
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = line[len("data: "):]
        events.append((event, json.loads(data)))
    return events


class RetrievalGroundingTests(TestCase):
    """chat/retrieval.py is the whole point of "grounded" — these pin the
    guarantee that a draft or placeholder-filled record can never be cited
    to a visitor, no matter how well its words match the query."""

    @classmethod
    def setUpTestData(cls):
        cluster = ServiceCluster.objects.create(name="Test Cluster", slug="test-cluster")
        cls.draft_service = Service.objects.create(
            cluster=cluster, title="Quantum Widget Automation",
            slug="quantum-widget-automation",
            tagline="Zyloflex agents for your qubit pipeline",
            summary="We build zyloflex quantum widget automation for regulated industries.",
            status=Service.Status.DRAFT,
        )
        cls.placeholder_service = Service.objects.create(
            cluster=cluster, title="Blorptastic Consulting",
            slug="blorptastic-consulting",
            tagline="[Placeholder] Blorptastic tagline",
            summary="[Placeholder] Blorptastic summary for cards.",
            status=Service.Status.PUBLISHED, published_at=timezone.now(),
        )
        cls.live_service = Service.objects.create(
            cluster=cluster, title="Real Published Widgetry",
            slug="real-published-widgetry",
            tagline="Genuinely shipped widget automation",
            summary="We actually build and ship widget automation systems for clients.",
            status=Service.Status.PUBLISHED, published_at=timezone.now(),
        )
        cls.draft_case_study = CaseStudy.objects.create(
            title="Zyloflex Draft Case Study", slug="zyloflex-draft-case-study",
            client_name="Zyloflex Corp",
            excerpt="Zyloflex quantum widget automation rollout for a regulated client.",
            status=CaseStudy.Status.DRAFT,
        )

    def test_draft_service_never_retrieved(self):
        chunks = retrieve("zyloflex quantum widget automation qubit")
        urls = [c.url for c in chunks]
        self.assertNotIn(self.draft_service.get_absolute_url(), urls)

    def test_placeholder_service_never_retrieved(self):
        chunks = retrieve("blorptastic consulting")
        urls = [c.url for c in chunks]
        self.assertNotIn(self.placeholder_service.get_absolute_url(), urls)

    def test_draft_case_study_never_retrieved(self):
        chunks = retrieve("zyloflex quantum widget automation rollout regulated")
        urls = [c.url for c in chunks]
        self.assertNotIn(self.draft_case_study.get_absolute_url(), urls)

    def test_live_clean_service_is_retrievable(self):
        chunks = retrieve("published widgetry automation systems")
        urls = [c.url for c in chunks]
        self.assertIn(self.live_service.get_absolute_url(), urls)

    def test_no_placeholder_marker_ever_appears_in_returned_text(self):
        for query in ["zyloflex", "blorptastic", "quantum widget", "automation"]:
            for chunk in retrieve(query):
                self.assertNotIn("[Placeholder]", chunk.text)
                self.assertNotIn("[TODO]", chunk.text)


@override_settings(ANTHROPIC_API_KEY="test-key-not-real")
class RefusalPathTests(TestCase):
    """When retrieval finds nothing relevant, the view must refuse without
    ever calling the Anthropic API — see chat/views.py::_no_answer_stream."""

    def setUp(self):
        cache.clear()

    def test_gibberish_query_gets_refusal_not_a_guess(self):
        response = self.client.post(
            "/forms/chat/message/",
            data=json.dumps({"message": "asdkfjqpwoeiruxzvnmqwpeoiruqwpoeiru gibberish"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        events = _sse_events(response)
        event_types = [e for e, _ in events]
        self.assertEqual(event_types, ["sources", "text", "done"])
        self.assertEqual(events[0][1], [])
        self.assertIn("don't have anything", events[1][1])

    def test_refusal_is_persisted_with_zero_tokens_and_no_sources(self):
        response = self.client.post(
            "/forms/chat/message/",
            data=json.dumps({"message": "zzqxwqpoeiru nonsense query zzqxw"}),
            content_type="application/json",
        )
        _sse_events(response)  # forces the streaming generator to run to completion
        message = ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT)
        self.assertEqual(message.tokens_used, 0)
        self.assertEqual(message.cited_sources, [])


@override_settings(ANTHROPIC_API_KEY="test-key-not-real")
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_rate_limit_blocks_after_threshold(self):
        for i in range(30):
            self.client.post(
                "/forms/chat/message/",
                data=json.dumps({"message": f"question number {i}"}),
                content_type="application/json",
            )

        response = self.client.post(
            "/forms/chat/message/",
            data=json.dumps({"message": "one more question"}),
            content_type="application/json",
        )
        events = _sse_events(response)
        self.assertEqual(events[0][0], "degrade")
        self.assertIn("Too many messages", events[0][1]["reason"])


@override_settings(ANTHROPIC_API_KEY="test-key-not-real", CHAT_DAILY_TOKEN_BUDGET=1000)
class BudgetExhaustionTests(TestCase):
    """Exceeding CHAT_DAILY_TOKEN_BUDGET must degrade the widget to a
    contact-form pointer, never a 500 or a silent overspend."""

    def setUp(self):
        cache.clear()

    def test_budget_exhausted_degrades_without_calling_the_api(self):
        conversation = ChatConversation.objects.create(session_key="preexisting")
        ChatMessage.objects.create(
            conversation=conversation, role=ChatMessage.Role.ASSISTANT,
            content="prior reply", tokens_used=1500,
        )
        self.assertEqual(ChatMessage.objects.count(), 1)

        response = self.client.post(
            "/forms/chat/message/",
            data=json.dumps({"message": "are you still there"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        events = _sse_events(response)
        self.assertEqual(events[0][0], "degrade")
        self.assertIn("usage limit for today", events[0][1]["reason"])
        # No new ChatMessage — the budget check runs before the user's
        # message is even persisted, so nothing was spent on this turn.
        self.assertEqual(ChatMessage.objects.count(), 1)


class WidgetVisibilityTests(TestCase):
    """The launcher must not render at all with no API key — the site has
    to keep working with no chatbot, not show a launcher that fails on
    first click."""

    @override_settings(ANTHROPIC_API_KEY="")
    def test_widget_absent_when_key_unset(self):
        response = self.client.get("/")
        self.assertNotContains(response, 'x-data="chatWidget()"')
        self.assertNotContains(response, "chat-widget.js")

    @override_settings(ANTHROPIC_API_KEY="test-key-not-real")
    def test_widget_present_when_key_set(self):
        response = self.client.get("/")
        self.assertContains(response, 'x-data="chatWidget()"')
