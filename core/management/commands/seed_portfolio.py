"""Seeds the 24 non-iGaming case studies: 16 named projects plus 8 anonymised
entries whose real screenshots live in the excluded
~/Downloads/case-study-images/_verify_before_use/ folder and must never be
attributed or shown.

Idempotent: every CaseStudy is keyed on its slug via get_or_create, and
featured is re-applied on every run so reruns stay correct even if it was
hand-edited in between.

No real project narrative was supplied for any of these 24, so challenge/
approach/outcome/excerpt are all explicit [TODO] placeholders per CLAUDE.md —
don't invent copy. Industry is only set where a project obviously maps to one
of the six seed_demo industries; ambiguous ones are left unset rather than
force-fit. Metrics are a single [TODO] row per case study — no numbers exist
for these yet.

Hero images are NOT set here — run `attach_case_study_images` separately.
That command intentionally skips anonymised case studies, so the eight below
stay imageless by design, matching the requirement that anonymised entries
show a descriptor and never a client identifier.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from insights.models import CaseStudy, Metric
from taxonomy.models import Industry

FEATURED_SLUGS = {"tax-automation-platform"}

TODO_METRIC = ("[TODO]", "[TODO]")

TODO_EXCERPT = "[TODO] excerpt for {title}."
TODO_CHALLENGE = "<p>[TODO] What the client was up against.</p>"
TODO_APPROACH = "<p>[TODO] What we built and why.</p>"
TODO_OUTCOME = "<p>[TODO] What changed as a result.</p>"

# (slug, title, client_name, client_anonymous, industry_slug)
NAMED_PROJECTS = [
    ("pollo-ai", "Pollo AI", "Pollo AI", "saas-startups"),
    ("askfred", "AskFred", "AskFred", "saas-startups"),
    ("logistics-operations-platform", "Gemstone Logistics", "Gemstone Logistics", "logistics-supply-chain"),
    ("contractor-marketplace", "Good Contractors List", "Good Contractors List", None),
    ("tax-automation-platform", "MuseTax", "MuseTax", "fintech"),
    ("field-service-management", "Infinity Fire Prevention", "Infinity Fire Prevention", None),
    ("ecommerce-platform", "Archies Footwear", "Archies Footwear", "e-commerce-retail"),
    ("gardening-community-platform", "Gardenstead", "Gardenstead", None),
    ("shipping-management-saas", "Ship District", "Ship District", "logistics-supply-chain"),
    ("telemedicine-mobile-app", "MOSC Telemedicine", "MOSC Telemedicine", "healthcare"),
    ("dating-social-platform", "TrulyMadly", "TrulyMadly", None),
    ("news-aggregation-app", "Newsfeed", "Newsfeed", None),
    ("fashion-d2c-organic-growth", "The Merino Polo", "The Merino Polo", "e-commerce-retail"),
    ("home-security-local-seo", "Securelux", "Securelux", None),
    ("hvac-services-local-seo", "All Type Mech", "All Type Mech", None),
    ("medical-practice-organic-growth", "Carpal Tunnel Pros", "Carpal Tunnel Pros", "healthcare"),
]

# (slug, title/generic descriptor, industry_slug) — client_name is always
# blank and client_anonymous is always True.
ANONYMISED_PROJECTS = [
    ("conversational-ai-platform", "Conversational AI Platform", "saas-startups"),
    ("industrial-vision-inspection", "Industrial Vision Inspection", None),
    ("hr-automation-suite", "HR Automation Suite", "saas-startups"),
    ("contract-intelligence-system", "Contract Intelligence System", "saas-startups"),
    ("ai-email-workspace", "AI Email Workspace", "saas-startups"),
    ("clinical-ai-agents", "Clinical AI Agents", "healthcare"),
    ("food-delivery-marketplace", "Food Delivery Marketplace", None),
    ("same-day-delivery-platform", "Same-Day Delivery Platform", "logistics-supply-chain"),
]


class Command(BaseCommand):
    help = (
        "Seeds the 24 non-iGaming case studies (16 named, 8 anonymised). "
        "Idempotent. All DRAFT."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        industries = {i.slug: i for i in Industry.objects.all()}

        for slug, title, client_name, industry_slug in NAMED_PROJECTS:
            self._seed_one(
                slug=slug, title=title, client_name=client_name,
                client_anonymous=False,
                industry=industries.get(industry_slug),
            )

        for slug, title, industry_slug in ANONYMISED_PROJECTS:
            self._seed_one(
                slug=slug, title=title, client_name="",
                client_anonymous=True,
                industry=industries.get(industry_slug),
            )

        self.stdout.write(self.style.SUCCESS("seed_portfolio complete."))

    def _seed_one(self, *, slug, title, client_name, client_anonymous, industry):
        obj, created = CaseStudy.objects.get_or_create(
            slug=slug,
            defaults=dict(
                title=title,
                excerpt=TODO_EXCERPT.format(title=title),
                client_name=client_name,
                client_anonymous=client_anonymous,
                industry=industry,
                challenge=TODO_CHALLENGE,
                approach=TODO_APPROACH,
                outcome=TODO_OUTCOME,
                hero_alt=title,
                status=CaseStudy.Status.DRAFT,
            ),
        )
        obj.featured = slug in FEATURED_SLUGS
        obj.save()

        Metric.objects.get_or_create(
            case_study=obj, label=TODO_METRIC[1],
            defaults=dict(value=TODO_METRIC[0], order=0),
        )

        self.stdout.write(f"{'Created' if created else 'Already existed'}: {obj.title}")
