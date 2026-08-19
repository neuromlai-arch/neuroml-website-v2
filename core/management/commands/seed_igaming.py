"""Seeds the six iGaming case studies from NeuroML's own portfolio PDF
(~/Downloads/NeuroML-iGaming-Portfolio.pdf) — real clients, real live URLs,
real delivered-modules copy pulled from that document.

Idempotent: every CaseStudy is keyed on its slug via get_or_create, and
featured/industry/blurb are re-applied on every run so reruns stay correct
even if fields were hand-edited in between.

Everything is created as DRAFT deliberately — this seeds data, it does not
publish it. Metrics are only set where the source PDF states a real figure
(Awash Bet: 840+ live soccer events, 12+ sports; FunBet: 4 brands on one
shared platform core). Every other metric slot is left as an explicit [TODO]
row rather than an invented number, per CLAUDE.md.

Hero images are NOT set here — run `attach_case_study_images` separately to
attach the real screenshots from ~/Downloads/case-study-images/.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from insights.models import CaseStudy, Metric
from taxonomy.models import Industry

INDUSTRY_NAME = "iGaming & Sweepstakes"
INDUSTRY_BLURB = (
    "Platform engineering for licensed operators — sportsbook, casino, "
    "wallet ledger and multi-tenant architecture."
)

FEATURED_SLUGS = {"betvaro", "awash-bet", "funbet"}

TODO_METRIC = ("[TODO]", "[TODO]")

STUDIES = [
    dict(
        slug="betvaro",
        title="BetVaro — A Custom Sportsbook and Casino Platform Built for Regulated Europe",
        client_name="BetVaro",
        excerpt=(
            "A ground-up sportsbook and casino platform for the European Union, with the "
            "wallet ledger, odds ingestion, risk engine and back office all designed and "
            "owned in-house."
        ),
        challenge=(
            "<p>BetVaro needed a platform engineered for regulated European markets, where "
            "compliance depth and margin control matter more than speed of launch — a custom "
            "build rather than a white-label deployment.</p>"
        ),
        approach=(
            "<p>Every layer — wallet ledger, odds ingestion, risk engine and back office — "
            "was designed and owned in-house. The home page leads with Top Combos: curated "
            "multi-leg betslips shown with live take-up counts and total odds, turning other "
            "players' selections into a discovery mechanism rather than relying on "
            "promotional banners alone.</p>"
            "<ul>"
            "<li><strong>Double-entry wallet ledger</strong> — Immutable transaction ledger "
            "with multi-currency balances and full audit replay.</li>"
            "<li><strong>Top Combos & Match Center</strong> — Curated multi-leg betslips "
            "surfaced with live take-up counts, combi size and total odds.</li>"
            "<li><strong>Risk & trading desk</strong> — Liability exposure dashboards, "
            "per-market limits and automated suspension rules.</li>"
            "<li><strong>Regulatory tooling</strong> — GDPR data-subject workflows, "
            "geo-fencing and jurisdiction-scoped content rules.</li>"
            "</ul>"
        ),
        outcome=(
            '<p>Live in production at <a href="https://www.betvaro.com/">betvaro.com</a>, '
            "with full source ownership across a custom sportsbook and casino core built "
            "for the European Union.</p>"
        ),
        metrics=[TODO_METRIC],
    ),
    dict(
        slug="awash-bet",
        title="Awash Bet — A Sportsbook-Led White-Label Platform for Ethiopia",
        client_name="Awash Bet",
        excerpt=(
            "A sportsbook-first white-label operator for the Ethiopian market, carrying "
            "more than 840 live soccer events alongside basketball, tennis, cricket and "
            "eSports."
        ),
        challenge=(
            "<p>Awash Bet needed a fast-narrowing sportsbook lobby that could carry a high "
            "volume of live soccer events alongside multiple other sports, with a betting "
            "board that switches markets without a page reload.</p>"
        ),
        approach=(
            "<ul>"
            "<li><strong>Pre-match & in-play</strong> — Live scores and minute tracking "
            "with in-running odds across 12+ sports.</li>"
            "<li><strong>Multi-market board</strong> — 1X2, Over/Under, Double Chance and "
            "Both Teams To Score switched inline across every fixture.</li>"
            "<li><strong>Booking codes & coupons</strong> — Players share and load "
            "ready-made slips by coupon ID or book code.</li>"
            "<li><strong>Step Cashback engine</strong> — Tiered cashback and a recurring "
            "Cashback Race running against live turnover.</li>"
            "</ul>"
        ),
        outcome=(
            '<p>Live in production at <a href="https://www.awashbet.cc/">awashbet.cc</a> '
            "as a white-label deployment on the shared platform core.</p>"
        ),
        metrics=[("840+", "Live soccer events"), ("12+", "Sports covered")],
    ),
    dict(
        slug="prime-stakes",
        title="Prime Stakes — A Casino-Led White-Label Platform for Nigeria",
        client_name="Prime Stakes",
        excerpt=(
            "A casino-forward brand trading in Nigerian naira, built to solve discovery "
            "across a catalogue running to thousands of titles from dozens of providers."
        ),
        challenge=(
            "<p>Prime Stakes' commercial problem was discovery: a catalogue running to "
            "thousands of titles across dozens of providers, in a market trading in "
            "Nigerian naira.</p>"
        ),
        approach=(
            "<ul>"
            "<li><strong>Multi-provider aggregation</strong> — Unified catalogue spanning "
            "slots, arcade, table, lottery and instant titles.</li>"
            "<li><strong>Crash & instant vertical</strong> — Dedicated Crash Legends rail "
            "carrying Aviator, Aviatrix, Plinko and Aero.</li>"
            "<li><strong>Live big-win ticker</strong> — Real-time winning feed with masked "
            "player IDs and settled NGN amounts.</li>"
            "<li><strong>Search & category rails</strong> — Provider search plus curated "
            "rails including Crowd Favourites and Hot Events.</li>"
            "</ul>"
        ),
        outcome=(
            '<p>Live in production at <a href="https://www.primestakes.com/">primestakes.com'
            "</a>, a white-label deployment focused on game discovery.</p>"
        ),
        metrics=[TODO_METRIC],
    ),
    dict(
        slug="funbet",
        title="FunBet — A Second Brand on Awash Bet's Shared Platform Core",
        client_name="FunBet",
        excerpt=(
            "A second sportsbook brand running on the same platform core as Awash Bet — "
            "the clearest demonstration of multi-tenant architecture in the portfolio."
        ),
        challenge=(
            "<p>FunBet needed its own domain, player base, welcome bonus and brand "
            "identity — launched fast, without forking the codebase already running Awash "
            "Bet.</p>"
        ),
        approach=(
            "<ul>"
            "<li><strong>Multi-tenant theming</strong> — Brand tokens, logo, palette and "
            "copy resolved per tenant from one build.</li>"
            "<li><strong>Independent campaigns</strong> — Own welcome bonus, refer-a-friend "
            "and promotional calendar per brand.</li>"
            "<li><strong>Shared platform core</strong> — One tested codebase, so a fix or "
            "new market ships to every brand at once.</li>"
            "<li><strong>Isolated operations</strong> — Separate reporting, player base and "
            "settlement under a common control plane.</li>"
            "</ul>"
        ),
        outcome=(
            '<p>Live in production at <a href="https://www.funbet.co.ke/">funbet.co.ke</a>. '
            "Awash Bet, FunBet, Prime Stakes and MaliBets all run on shared platform cores "
            "with per-brand theming — one tested codebase serving four brands, so a fix or "
            "a new market ships to all of them at once.</p>"
        ),
        metrics=[("4", "Brands on one shared platform core")],
    ),
    dict(
        slug="malibets",
        title="MaliBets — A Crash-Led Casino Platform for Kenya",
        client_name="MaliBets",
        excerpt=(
            "A Kenyan casino brand built around crash and instant-win titles, the format "
            "that dominates East African play, sharing one wallet across casino and sports."
        ),
        challenge=(
            "<p>MaliBets needed a lobby built around crash and instant-win titles — the "
            "format that dominates East African play because rounds are seconds long and "
            "stakes are small — while still converting sports-led traffic.</p>"
        ),
        approach=(
            "<ul>"
            "<li><strong>Crash & instant lobby</strong> — Crash-first rail carrying Matatu, "
            "Astronaut, Aero, Aviajet and Crash for Six.</li>"
            "<li><strong>Sports crossover</strong> — Popular Matches strip with live 1X2 "
            "odds embedded in the casino home.</li>"
            "<li><strong>Curated discovery rails</strong> — Crowd Favourites, Most Popular "
            "and provider-level filtering across the catalogue.</li>"
            "<li><strong>Bonus & retention engine</strong> — 100% welcome bonus with "
            "campaign tooling and re-engagement triggers.</li>"
            "</ul>"
        ),
        outcome=(
            '<p>Live in production at <a href="https://www.malibets.co.ke/">malibets.co.ke'
            "</a>, mobile-first with crash games as the lead product.</p>"
        ),
        metrics=[TODO_METRIC],
    ),
    dict(
        slug="lastabet",
        title="Lastabet — A Multi-Market Sportsbook Across Africa",
        client_name="Lastabet",
        excerpt=(
            "A sportsbook brand operating across multiple African territories, with "
            "currency, language and payment provider handled as configuration rather than "
            "code."
        ),
        challenge=(
            "<p>Lastabet needed to operate across multiple African territories without "
            "forking the codebase per market — currency, language and payment provider all "
            "had to become configuration, not code.</p>"
        ),
        approach=(
            "<ul>"
            "<li><strong>Jackpot & pool betting</strong> — Fixed-fixture jackpot slips with "
            "automated settlement and prize splitting.</li>"
            "<li><strong>Territory configuration</strong> — Currency, language and provider "
            "routing switched per market.</li>"
            "<li><strong>Full sportsbook markets</strong> — Pre-match and live across "
            "football, basketball and regional leagues.</li>"
            "<li><strong>Operational reporting</strong> — Turnover, margin and liability "
            "reporting segmented by territory.</li>"
            "</ul>"
        ),
        outcome=(
            '<p>Live in production at <a href="https://www.lastabet.com/">lastabet.com</a> '
            "across multiple African markets, with jackpot products as a low-stake, "
            "high-engagement acquisition hook.</p>"
        ),
        metrics=[TODO_METRIC],
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds the six iGaming case studies (BetVaro, Awash Bet, Prime Stakes, FunBet, "
        "MaliBets, Lastabet) from NeuroML's own portfolio PDF. Idempotent. All DRAFT."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        industry = self._seed_industry()

        for entry in STUDIES:
            obj, created = CaseStudy.objects.get_or_create(
                slug=entry["slug"],
                defaults=dict(
                    title=entry["title"],
                    excerpt=entry["excerpt"],
                    client_name=entry["client_name"],
                    client_anonymous=False,
                    industry=industry,
                    challenge=entry["challenge"],
                    approach=entry["approach"],
                    outcome=entry["outcome"],
                    hero_alt=entry["title"],
                    status=CaseStudy.Status.DRAFT,
                ),
            )
            obj.featured = entry["slug"] in FEATURED_SLUGS
            obj.save()

            for order, (value, label) in enumerate(entry["metrics"]):
                Metric.objects.get_or_create(
                    case_study=obj, label=label,
                    defaults=dict(value=value, order=order),
                )

            self.stdout.write(f"{'Created' if created else 'Already existed'}: {obj.title}")

        self.stdout.write(self.style.SUCCESS("seed_igaming complete."))

    def _seed_industry(self):
        industry, _ = Industry.objects.get_or_create(
            slug=slugify(INDUSTRY_NAME),
            defaults=dict(name=INDUSTRY_NAME, blurb=INDUSTRY_BLURB),
        )
        if industry.blurb != INDUSTRY_BLURB:
            industry.blurb = INDUSTRY_BLURB
            industry.save(update_fields=["blurb"])
        return industry
