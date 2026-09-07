"""Applies the approved fixes from the case-study content-quality audit
(2026-09-02): unpublish the 4 seed_portfolio placeholder studies, drop the
literal [TODO] metric rows on the 4 real iGaming studies still carrying
them, attach service tags to the 6 real iGaming studies based only on what
each one's own challenge/approach/outcome copy describes, and set a unique
meta_description on all 10.

Idempotent — every write is a direct field/M2M set, safe to rerun.

Deliberately NOT touched here (see audit): the 4 placeholder studies' wrong
service/industry tags. They stay as-is, documented below, until real
content replaces the placeholder copy — reassigning tags on content that's
about to be rewritten wastes the pass.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Publishable
from insights.models import CaseStudy, Metric

# ---------------------------------------------------------------------------
# 1. Unpublish + noindex the 4 seed_portfolio placeholder studies.
# ---------------------------------------------------------------------------
PLACEHOLDER_SLUGS = [
    "clinical-document-extraction-at-scale",
    "fraud-triage-copilot-for-a-regional-bank",
    "automating-rfp-response-for-a-logistics-leader",
    "cutting-stockouts-with-a-demand-forecasting-agent",
]
PLACEHOLDER_META_DESCRIPTION = (
    "[Placeholder] This case study is not yet published — real client "
    "content is pending before it goes live."
)

# Documented, NOT applied yet — see module docstring. Correct tags to apply
# once real content replaces the placeholder copy on each of these:
#   fraud-triage-copilot-for-a-regional-bank: drop 'digital-marketing'
#     (irrelevant to a fraud-triage copilot), keep 'ml-engineering-mlops'
#   automating-rfp-response-for-a-logistics-leader: drop 'seo' and
#     'digital-marketing' (both irrelevant to an AI/document-automation
#     case study)
#   cutting-stockouts-with-a-demand-forecasting-agent: drop 'seo'
#     (irrelevant); industry is currently "iGaming & Sweepstakes", which
#     doesn't match a stockout/demand-forecasting case study — needs a
#     real industry once the content is written

# ---------------------------------------------------------------------------
# 2. Real iGaming studies: drop their [TODO]/[TODO] metric row.
# ---------------------------------------------------------------------------
TODO_METRIC_SLUGS = ["prime-stakes", "betvaro", "malibets", "lastabet"]

# ---------------------------------------------------------------------------
# 3. Real iGaming studies: service tags, justified per-study (see audit —
#    based only on what each case study's own copy says was delivered; no
#    service is applied to every study by default).
# ---------------------------------------------------------------------------
IGAMING_SERVICE_TAGS = {
    # Catalogue/discovery UI and a real-time feed — product/frontend+backend
    # feature work, no stated ground-up infra build.
    "prime-stakes": ["full-stack-development"],
    # Explicitly "designed and owned in-house": wallet ledger, odds
    # ingestion, risk engine, back office (custom-software-development),
    # plus a full delivered UI — Top Combos, Match Center
    # (full-stack-development).
    "betvaro": ["custom-software-development", "full-stack-development"],
    # The case study IS the multi-tenant architecture story — shared
    # platform core, per-brand theming, isolated operations. Architecture,
    # not a features list.
    "funbet": ["custom-software-development"],
    # Sportsbook feature/UI work (live odds board, booking codes, cashback
    # engine) on the shared platform core described in funbet's case study.
    "awash-bet": ["full-stack-development"],
    # Same pattern as prime-stakes: lobby/discovery UI plus a bonus engine,
    # product feature work.
    "malibets": ["full-stack-development"],
    # Challenge and first approach bullet are explicitly architectural
    # ("currency, language and payment provider ... configuration, not
    # code") — custom-software-development — plus full sportsbook markets
    # UI and reporting — full-stack-development.
    "lastabet": ["custom-software-development", "full-stack-development"],
}

# ---------------------------------------------------------------------------
# 4. Unique meta_description for all 10 (real ones describe actual
#    delivered work from the case study's own copy; placeholder ones state
#    plainly that the page isn't live yet — no invented claims either way).
# ---------------------------------------------------------------------------
META_DESCRIPTIONS = {
    "prime-stakes": (
        "How we built game discovery for Prime Stakes, a Nigerian casino "
        "platform aggregating thousands of titles across dozens of providers."
    ),
    "betvaro": (
        "BetVaro: a custom sportsbook and casino platform for the EU, with "
        "an in-house wallet ledger, odds ingestion, risk engine and back office."
    ),
    "funbet": (
        "How FunBet launched as a second sportsbook brand on Awash Bet's "
        "shared platform core — one codebase running four independently "
        "operated brands."
    ),
    "awash-bet": (
        "Awash Bet: a white-label sportsbook platform for Ethiopia carrying "
        "840+ live soccer events and 12+ sports on a real-time betting board."
    ),
    "malibets": (
        "MaliBets: a Kenyan casino platform built around crash and "
        "instant-win games, the format driving East African play, on a "
        "shared wallet."
    ),
    "lastabet": (
        "Lastabet: a multi-market African sportsbook where currency, "
        "language and payment provider are configuration, not a per-market "
        "code fork."
    ),
    "clinical-document-extraction-at-scale": PLACEHOLDER_META_DESCRIPTION,
    "fraud-triage-copilot-for-a-regional-bank": PLACEHOLDER_META_DESCRIPTION,
    "automating-rfp-response-for-a-logistics-leader": PLACEHOLDER_META_DESCRIPTION,
    "cutting-stockouts-with-a-demand-forecasting-agent": PLACEHOLDER_META_DESCRIPTION,
}


class Command(BaseCommand):
    help = "Applies the approved fixes from the 2026-09-02 case-study content-quality audit."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Unpublish + noindex the placeholder studies. Preserves the
        # record (draft, not deleted) for future real content.
        unpublished = CaseStudy.objects.filter(slug__in=PLACEHOLDER_SLUGS).update(
            status=Publishable.Status.DRAFT, noindex=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f"unpublished + noindexed {unpublished} placeholder case studies"
        ))

        # 2. Drop the [TODO]/[TODO] metric rows.
        deleted, _ = Metric.objects.filter(
            case_study__slug__in=TODO_METRIC_SLUGS, value="[TODO]", label="[TODO]",
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"deleted {deleted} [TODO] metric row(s)"))

        # 3. Service tags on the real iGaming studies.
        for slug, service_slugs in IGAMING_SERVICE_TAGS.items():
            case_study = CaseStudy.objects.get(slug=slug)
            case_study.services.set(list(
                case_study.services.model.objects.filter(slug__in=service_slugs)
            ))
            self.stdout.write(f"  {slug} -> services: {service_slugs}")

        # 4. Meta descriptions on all 10.
        for slug, description in META_DESCRIPTIONS.items():
            CaseStudy.objects.filter(slug=slug).update(meta_description=description)
        self.stdout.write(self.style.SUCCESS(
            f"set meta_description on {len(META_DESCRIPTIONS)} case studies"
        ))

        self.stdout.write(self.style.SUCCESS("Done."))
