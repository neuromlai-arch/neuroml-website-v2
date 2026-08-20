"""Grounded retrieval for the chat widget: PostgreSQL full-text search over
published content only. No vector database — this corpus (a few dozen
services, case studies, FAQs, industries, and comparison rows) is small
enough that FTS ranking is sufficient. Revisit with a vector store only if
retrieval quality turns out to be poor in practice; don't add one pre-emptively.

Every queryset here is hand-filtered rather than just reusing `.live()` /
`.filter(active=True)` — a record can be published and still contain literal
"[TODO]" or "[Placeholder]" filler (see the content-audit work earlier this
project). Grounding an answer in that text would put fabricated-looking copy
in front of a visitor as if it were real, which defeats the entire point of
grounding. Never loosen PLACEHOLDER_MARKERS or drop a filter here without
re-verifying that guarantee — there are tests pinned to it
(chat/tests.py::RetrievalGroundingTests).
"""

from dataclasses import dataclass

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q
from django.utils.html import strip_tags

from insights.models import CaseStudy
from marketing.models import ComparisonTable
from pages.models import HomePage
from solutions.models import Service
from taxonomy.models import Industry

PLACEHOLDER_MARKERS = ("[TODO", "[Placeholder")

# Below this rank, a match is noise, not a citation — same threshold used by
# the "did retrieval actually find anything" check in generation.py.
MIN_RANK = 0.01


def _clean_text(*, no_placeholder_fields, **kwargs):
    """True if none of the given field values contain a placeholder marker."""
    for value in no_placeholder_fields:
        if not value:
            continue
        if any(marker in value for marker in PLACEHOLDER_MARKERS):
            return False
    return True


@dataclass(frozen=True)
class RetrievedChunk:
    title: str
    url: str
    text: str
    rank: float


def _build_query(query_text):
    """OR-combined per-word query rather than websearch_to_tsquery's default
    AND-of-all-words — a visitor's question is not a boolean search string,
    and requiring every word to co-occur in a short summary/tagline made
    real matches disappear (e.g. "do you build agents" needs "build" AND
    "agent" together, but a service's tagline says "agents", never "build")."""
    terms = [t for t in query_text.split() if len(t) > 1]
    if not terms:
        return None
    query = SearchQuery(terms[0])
    for term in terms[1:]:
        query |= SearchQuery(term)
    return query


def _rank_and_collect(queryset, vector_fields, query_text, to_chunk, limit):
    vector = SearchVector(*vector_fields)
    query = _build_query(query_text)
    if query is None:
        return []
    ranked = (
        queryset
        .annotate(rank=SearchRank(vector, query))
        .filter(rank__gt=MIN_RANK)
        .order_by("-rank")[:limit]
    )
    chunks = []
    for obj in ranked:
        chunk = to_chunk(obj)
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def _search_services(query_text, limit):
    def to_chunk(service):
        if not _clean_text(no_placeholder_fields=[service.tagline, service.summary]):
            return None
        body_text = ""
        if service.body and _clean_text(no_placeholder_fields=[service.body]):
            body_text = " " + strip_tags(service.body)
        text = f"{service.tagline} {service.summary}{body_text}".strip()
        if not text:
            return None
        return RetrievedChunk(
            title=service.title, url=service.get_absolute_url(),
            text=text, rank=service.rank,
        )

    qs = Service.objects.live().exclude(summary="")
    return _rank_and_collect(qs, ["tagline", "summary", "body"], query_text, to_chunk, limit)


def _search_case_studies(query_text, limit):
    def to_chunk(cs):
        fields = [cs.excerpt, cs.challenge, cs.approach, cs.outcome]
        clean_fields = [strip_tags(f) for f in fields if f and _clean_text(no_placeholder_fields=[f])]
        if not clean_fields:
            return None
        text = f"{cs.display_client} — {cs.title}. " + " ".join(clean_fields)
        return RetrievedChunk(
            title=cs.title, url=cs.get_absolute_url(), text=text, rank=cs.rank,
        )

    qs = CaseStudy.objects.live().exclude(excerpt="")
    return _rank_and_collect(
        qs, ["title", "excerpt", "challenge", "approach", "outcome"],
        query_text, to_chunk, limit,
    )


def _search_faqs(query_text, limit):
    from marketing.models import FAQ

    def to_chunk(faq):
        answer_text = strip_tags(faq.answer)
        if not _clean_text(no_placeholder_fields=[faq.question, answer_text]):
            return None
        return RetrievedChunk(
            title=faq.question, url="/contact/", text=f"{faq.question} {answer_text}",
            rank=faq.rank,
        )

    qs = FAQ.objects.filter(active=True)
    return _rank_and_collect(qs, ["question", "answer"], query_text, to_chunk, limit)


def _search_industries(query_text, limit):
    def to_chunk(industry):
        if not industry.blurb or not _clean_text(no_placeholder_fields=[industry.blurb]):
            return None
        return RetrievedChunk(
            title=industry.name, url=industry.get_absolute_url(),
            text=f"{industry.name}: {industry.blurb}", rank=industry.rank,
        )

    qs = Industry.objects.exclude(blurb="")
    return _rank_and_collect(qs, ["name", "blurb"], query_text, to_chunk, limit)


def _search_comparison_rows(query_text, limit):
    def to_chunk(table):
        if not _clean_text(no_placeholder_fields=[table.title, table.intro]):
            return None
        rows = table.rows.all()
        row_lines = []
        for row in rows:
            values = [row.column_1_value, row.column_2_value, row.column_3_value]
            if not _clean_text(no_placeholder_fields=[row.criterion] + values):
                continue
            row_lines.append(
                f"{row.criterion}: {table.column_1_label}={row.column_1_value}, "
                f"{table.column_2_label}={row.column_2_value}, "
                f"{table.column_3_label}={row.column_3_value}"
            )
        if not row_lines:
            return None
        text = f"{table.title}. {table.intro} " + " | ".join(row_lines)
        return RetrievedChunk(title=table.title, url="/#contact", text=text, rank=table.rank)

    qs = ComparisonTable.objects.filter(active=True).prefetch_related("rows")
    return _rank_and_collect(qs, ["title", "intro"], query_text, to_chunk, limit)


def _search_homepage(query_text, limit):
    home = HomePage.objects.first()
    if home is None:
        return []
    fields = [
        home.hero_heading, home.hero_subheading,
        home.expertise_heading, home.expertise_intro,
    ]
    if not _clean_text(no_placeholder_fields=fields):
        return []
    text = " ".join(f for f in fields if f).strip()
    if not text:
        return []
    # No SearchRank machinery for a single singleton row — a plain substring
    # relevance check keeps this consistent with everything else being
    # ranked, without a query just to rank one record.
    query_terms = [t.lower() for t in query_text.split() if len(t) > 2]
    if not query_terms or not any(t in text.lower() for t in query_terms):
        return []
    # A flat rank in the same ballpark as a solid FTS match elsewhere — high
    # enough to surface when it's genuinely the best answer (e.g. "what do
    # you do"), not so high it reflexively wins the top slot on every query
    # that happens to share a word with the hero copy.
    return [RetrievedChunk(title="About the studio", url="/", text=text, rank=0.15)]


def retrieve(query_text, limit=5):
    """Returns up to `limit` RetrievedChunk objects across all groundable
    content types, ranked highest-first. Empty list means "nothing relevant
    was found" — the caller (generation.py) must refuse to answer rather
    than fall back to the model's general knowledge."""
    if not query_text or not query_text.strip():
        return []

    candidates = []
    candidates += _search_services(query_text, limit)
    candidates += _search_case_studies(query_text, limit)
    candidates += _search_faqs(query_text, limit)
    candidates += _search_industries(query_text, limit)
    candidates += _search_comparison_rows(query_text, limit)
    candidates += _search_homepage(query_text, limit)

    candidates.sort(key=lambda c: c.rank, reverse=True)
    return candidates[:limit]
