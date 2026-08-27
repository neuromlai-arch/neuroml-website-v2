"""Realistic placeholder content so every template section renders.

Idempotent: every object is keyed on a natural/unique field via
get_or_create, so running this twice doesn't duplicate anything. Pass
--flush to wipe every model this command manages first, for a clean reseed.

Nothing here is real copy — everything is prefixed "[Placeholder]" per
CLAUDE.md, and every image is a grey generated SVG (core/placeholders.py),
never a downloaded stock photo.

Deliberately NOT seeded: TeamMember, ClientLogo, Recognition, Office, Tag.
All five used to be seeded here, until a plain (non---flush) re-run kept
resurrecting rows someone had deliberately deleted — every _seed_* method
used get_or_create unconditionally, not just under --flush, so any row
matching a hardcoded natural key just came right back. Recognition and Tag
now hold real content too (real partner/award badges; a genuine "Computer
Vision" category), which made that actively wrong rather than just
dormant risk. This command now reads whatever real rows already exist for
these five (`list(Model.objects.all())`) instead of creating its own, and
degrades gracefully — no author, no tags, no badges — if none exist yet.
Don't re-add a _seed_* method for any of them; if a fresh dev DB needs
demo people/logos/badges/offices/tags again, add them by hand or write a
one-off script, not a get_or_create loop that runs on every invocation.

Everything else in this file is still fabricated placeholder content and is
safely re-seedable — see CLAUDE.md's "don't invent copy" rule for why it's
prefixed [TODO]/[Placeholder] rather than looking real.
"""

import random
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from careers.models import JobPosting
from core.placeholders import set_placeholder
from insights.models import BlogPost, CaseStudy, Handbook, Metric, Webinar
from marketing.models import (
    ComparisonRow, ComparisonTable, EngagementModel, FAQ,
    LeadPopup, Partner, PopupStep, ProcessStep, Recognition, Testimonial,
)
from pages.models import HomePage, SiteSettings
from people.models import TeamMember
from solutions.models import (
    HireRole, Product, Service, Technology, UseCase,
)
from taxonomy.models import Industry, ServiceCluster, Tag

PLACEHOLDER = "[Placeholder]"

FLUSH_MODELS = [
    PopupStep, LeadPopup, FAQ, ComparisonRow, ComparisonTable, EngagementModel,
    ProcessStep, Testimonial, Partner,
    JobPosting, Metric, Webinar, Handbook, CaseStudy, BlogPost,
    HireRole, Product, UseCase, Technology, Service,
    Industry, ServiceCluster,
    # SiteSettings/HomePage are singletons — left alone by --flush so the
    # site never briefly has no chrome; they're always get_or_create'd below.
    # TeamMember, ClientLogo, Recognition, Office, Tag are also deliberately
    # absent — this command doesn't seed them (see the module docstring), so
    # --flush must not delete real rows it can't recreate.
]


def days_ago(n):
    return timezone.now() - timedelta(days=n)


def days_from_now(n):
    return timezone.now() + timedelta(days=n)


class Command(BaseCommand):
    help = "Seeds realistic placeholder content across every app. Idempotent; --flush to reset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing seeded content (everything but the HomePage/SiteSettings "
                 "singletons) before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing content...")
            for model in FLUSH_MODELS:
                model.objects.all().delete()

        industries = self._seed_industries()
        clusters = self._seed_service_clusters()
        # Not seeded — see the module docstring. Whatever real rows already
        # exist get used; an empty list degrades gracefully below.
        tags = list(Tag.objects.all())
        team = list(TeamMember.objects.all())
        services = self._seed_services(clusters)
        technologies = self._seed_technologies(services)
        self._seed_use_cases(industries, services)
        self._seed_products(industries)
        self._seed_hire_roles(services, technologies)
        case_studies = self._seed_case_studies(industries, services, tags, team)
        self._seed_blog_posts(industries, services, tags, team)
        self._seed_handbooks(tags, team)
        self._seed_webinars(team, tags)
        self._seed_testimonials(case_studies)
        self._seed_partners()
        recognitions = list(Recognition.objects.all())
        self._seed_process_steps()
        self._seed_engagement_models()
        self._seed_comparison_table()
        self._seed_faqs(services)
        self._seed_job_postings()
        self._seed_site_settings()
        self._seed_homepage()
        self._seed_lead_popup(recognitions)

        self.stdout.write(self.style.SUCCESS("seed_demo complete."))

    # ------------------------------------------------------------ taxonomy

    def _seed_industries(self):
        names = [
            "iGaming & Sweepstakes", "E-commerce & Retail", "Fintech",
            "Healthcare", "Logistics & Supply Chain", "SaaS & Startups",
        ]
        out = []
        for i, name in enumerate(names):
            obj, created = Industry.objects.get_or_create(
                slug=slugify(name),
                defaults=dict(
                    name=name,
                    blurb=f"[TODO] How AI changes {name.lower()}.",
                    order=i,
                ),
            )
            if created:
                set_placeholder(obj, "icon", 96, 96, name.split()[0], slug=f"industry-{obj.slug}")
                obj.save()
            out.append(obj)
        return out

    def _seed_service_clusters(self):
        """Real taxonomy — order is deliberate (1-indexed, not enumerate-based)."""
        entries = [
            ("AI & Machine Learning", 1),
            ("Product Engineering", 2),
            ("Growth", 3),
        ]
        out = []
        for name, order in entries:
            obj, _ = ServiceCluster.objects.get_or_create(
                slug=slugify(name),
                defaults=dict(
                    name=name,
                    blurb=f"[TODO] {name} services, built for production.",
                    order=order,
                ),
            )
            out.append(obj)
        return out

    # ------------------------------------------------------------ solutions

    def _seed_services(self, clusters):
        """11 total, all top-level for now — nesting comes later if a
        cluster grows. Taglines here are final copy, used verbatim; summary
        and body are still placeholder, marked [TODO]."""
        ai_ml, product_eng, growth = clusters
        plan = [
            (ai_ml, True, [
                ("AI Agents & Automation", "Autonomous agents that do real work, not demos"),
                ("RAG & Knowledge Systems", "Retrieval systems your team actually trusts"),
                ("LLM Application Development", "Production apps on OpenAI, Anthropic, and open models"),
                ("Computer Vision", "Detection, tracking, and inspection at production accuracy"),
                ("ML Engineering & MLOps", "Models that stay accurate after launch"),
            ]),
            (product_eng, True, [
                ("Full-Stack Development", "React, Next.js, FastAPI, Django, NestJS"),
                ("Custom Software Development", "Systems built for one business, not configured for many"),
                ("DevOps & Cloud", "AWS and GCP infrastructure that scales without drama"),
                ("Salesforce Development", "Custom Salesforce builds and integrations"),
            ]),
            (growth, False, [
                ("SEO", "Technical SEO and content that ranks"),
                ("Digital Marketing", "Performance marketing for technical products"),
            ]),
        ]
        out = []
        order = 0
        for cluster, show_in_form_dropdown, entries in plan:
            for title, tagline in entries:
                slug = slugify(title)
                obj, created = Service.objects.get_or_create(
                    slug=slug,
                    defaults=dict(
                        cluster=cluster, title=title, tagline=tagline,
                        summary=f"[TODO] {title} summary for cards and listings.",
                        body=f"<p>[TODO] Full body copy for {title}.</p>",
                        order=order, show_in_nav=True,
                        show_in_form_dropdown=show_in_form_dropdown,
                        status=Service.Status.PUBLISHED, published_at=days_ago(30),
                    ),
                )
                if created:
                    set_placeholder(obj, "icon", 64, 64, title[:2], slug=f"service-{slug}-icon")
                    set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"service-{slug}-hero")
                    obj.save()
                out.append(obj)
                order += 1
        return out

    def _seed_technologies(self, services):
        """Each technology is mapped to its real parent service by title.
        The first twelve (in the order below) show in the stack grid."""
        by_title = {s.title: s for s in services}
        entries = [
            ("Python", "Full-Stack Development"),
            ("FastAPI", "Full-Stack Development"),
            ("Django", "Full-Stack Development"),
            ("NestJS", "Full-Stack Development"),
            ("React", "Full-Stack Development"),
            ("Next.js", "Full-Stack Development"),
            ("React Native", "Full-Stack Development"),
            ("LangChain", "AI Agents & Automation"),
            ("LangGraph", "AI Agents & Automation"),
            ("OpenAI API", "LLM Application Development"),
            ("Anthropic API", "LLM Application Development"),
            ("PyTorch", "Computer Vision"),
            ("YOLO", "Computer Vision"),
            ("AWS", "DevOps & Cloud"),
            ("GCP", "DevOps & Cloud"),
            ("Docker", "DevOps & Cloud"),
            ("Kubernetes", "DevOps & Cloud"),
            ("PostgreSQL", "Custom Software Development"),
            ("Redis", "Custom Software Development"),
        ]
        out = []
        for i, (name, service_title) in enumerate(entries):
            slug = slugify(name)
            obj, created = Technology.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    service=by_title[service_title], name=name,
                    tagline=f"[TODO] How we use {name}.",
                    body=f"<p>[TODO] Full body copy for {name}.</p>",
                    order=i, show_in_stack_grid=(i < 12),
                    status=Technology.Status.PUBLISHED, published_at=days_ago(20),
                ),
            )
            if created:
                set_placeholder(obj, "logo", 200, 80, name, slug=f"tech-{slug}-logo")
                obj.save()
            out.append(obj)
        return out

    def _seed_use_cases(self, industries, services):
        """24 total: 4 per industry, all show_on_homepage=True.

        Real launch copy, one list per industry in the same order
        `_seed_industries` creates them — iGaming & Sweepstakes, E-commerce &
        Retail, Fintech, Healthcare, Logistics & Supply Chain, SaaS &
        Startups. Body stays [TODO]; only title/summary are real."""
        use_cases_by_industry = [
            [  # iGaming & Sweepstakes
                ("Real-time fraud and bonus abuse detection",
                 "Pattern detection across deposits, bets and withdrawals to flag "
                 "bonus abuse and collusion before payout rather than after."),
                ("Player risk and responsible gaming signals",
                 "Behavioural models surfacing session-length, chasing and "
                 "deposit-escalation patterns to the operator's responsible "
                 "gaming workflow."),
                ("Automated KYC document processing",
                 "OCR and extraction over identity documents with confidence "
                 "scoring and human escalation on anything ambiguous."),
                ("Support automation grounded in policy",
                 "Retrieval over your actual terms, bonus rules and withdrawal "
                 "policies, so answers cite the policy rather than approximate it."),
            ],
            [  # E-commerce & Retail
                ("Catalogue enrichment at scale",
                 "Generating structured attributes, descriptions and "
                 "categorisation across large catalogues from supplier data and "
                 "images."),
                ("Search that understands intent",
                 "Hybrid semantic and keyword search so a query for 'waterproof "
                 "jacket for hiking' returns the right products, not the ones "
                 "matching most words."),
                ("Returns and support triage",
                 "Automated classification and routing of support contacts, with "
                 "policy-grounded responses for the routine majority."),
                ("Demand and stock forecasting",
                 "Forecasting models over sales history, seasonality and "
                 "supplier lead times, with drift monitoring as patterns shift."),
            ],
            [  # Fintech
                ("Document intelligence for onboarding",
                 "Extraction from statements, filings and identity documents "
                 "with confidence thresholds and audit trails."),
                ("Transaction categorisation and enrichment",
                 "Classifying transaction streams into usable categories with "
                 "merchant enrichment and correction feedback loops."),
                ("Compliance monitoring and alerting",
                 "Pattern detection over transaction data with explainable "
                 "flags, built so a compliance officer can see why something "
                 "fired."),
                ("Customer support grounded in regulation",
                 "Retrieval systems that answer from your actual regulatory "
                 "position rather than generating plausible-sounding guidance."),
            ],
            [  # Healthcare
                ("Clinical document processing",
                 "Extraction and structuring from referrals, notes and reports, "
                 "with human review on anything below confidence threshold."),
                ("Patient communication automation",
                 "Appointment, reminder and follow-up workflows with escalation "
                 "paths to clinical staff."),
                ("Medical imaging support",
                 "Computer vision assisting review workflows, with accuracy "
                 "characterised by condition rather than reported as a single "
                 "number."),
                ("Knowledge retrieval for clinicians",
                 "Search across guidelines, protocols and internal policy that "
                 "cites sources and declines when uncertain."),
            ],
            [  # Logistics & Supply Chain
                ("Document automation across the chain",
                 "Extraction from bills of lading, customs forms and invoices, "
                 "handling the malformed and scanned reality of the paperwork."),
                ("Route and load optimisation",
                 "Optimisation over real constraints — vehicle capacity, driver "
                 "hours, delivery windows — rather than idealised ones."),
                ("Exception detection and triage",
                 "Detecting delays, mismatches and anomalies across tracking "
                 "data, and routing them to whoever can act."),
                ("Warehouse computer vision",
                 "Counting, condition checking and inventory verification from "
                 "existing camera infrastructure."),
            ],
            [  # SaaS & Startups
                ("AI features in your product",
                 "Building the AI feature your roadmap needs, with the cost "
                 "model and evaluation to run it at scale."),
                ("Retrieval over your own documentation",
                 "Support and onboarding assistants grounded in your real "
                 "docs, with citations users can check."),
                ("Usage analysis and churn signals",
                 "Models over product telemetry surfacing the behaviour that "
                 "precedes churn, with the caveats stated honestly."),
                ("Internal tooling agents",
                 "Agents handling triage, research and routine operations "
                 "against your internal systems."),
            ],
        ]

        order = 0
        for industry, use_cases in zip(industries, use_cases_by_industry):
            for i, (title, summary) in enumerate(use_cases, start=1):
                slug = slugify(title)
                obj, created = UseCase.objects.get_or_create(
                    slug=slug,
                    defaults=dict(
                        industry=industry,
                        related_service=services[order % len(services)],
                        title=title,
                        summary=summary,
                        body=f"<p>[TODO] Full body copy for {title}.</p>",
                        show_on_homepage=True, order=i,
                        status=UseCase.Status.PUBLISHED, published_at=days_ago(15),
                    ),
                )
                if created:
                    set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"usecase-{slug}-hero")
                    obj.save()
                order += 1

    def _seed_products(self, industries):
        products = [
            ("AI Agent for Logistics", industries[1:2]),
            ("AI Retail Assistant", industries[0:1]),
        ]
        for i, (title, prod_industries) in enumerate(products):
            slug = slugify(title)
            obj, created = Product.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title,
                    tagline=f"{PLACEHOLDER} Packaged offering: {title}.",
                    summary=f"{PLACEHOLDER} {title} summary.",
                    body=f"<p>{PLACEHOLDER} Full body copy for {title}.</p>",
                    order=i, show_in_nav=True,
                    status=Product.Status.PUBLISHED, published_at=days_ago(25),
                ),
            )
            if created:
                obj.industries.set(prod_industries)
                set_placeholder(obj, "card_image", 800, 600, title, slug=f"product-{slug}-card")
                set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"product-{slug}-hero")
                obj.save()

    def _seed_hire_roles(self, services, technologies):
        roles = [
            "Hire an AI Agent Engineer", "Hire an ML Platform Engineer",
            "Hire a Prompt & Evals Specialist",
        ]
        for i, title in enumerate(roles):
            slug = slugify(title)
            obj, created = HireRole.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title,
                    tagline=f"{PLACEHOLDER} Pitch for {title.lower()}.",
                    summary=f"{PLACEHOLDER} Summary for {title}.",
                    body=f"<p>{PLACEHOLDER} Full body copy for {title}.</p>",
                    starting_rate=f"${8 + i * 2}0/hr",
                    order=i,
                    status=HireRole.Status.PUBLISHED, published_at=days_ago(10),
                ),
            )
            if created:
                obj.skills.set(random.sample(technologies, k=min(4, len(technologies))))
                obj.related_services.set(random.sample(services, k=min(2, len(services))))
                set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"hire-{slug}-hero")
                obj.save()

    # ------------------------------------------------------------- insights

    def _seed_case_studies(self, industries, services, tags, team):
        studies = [
            ("Cutting Stockouts With a Demand Forecasting Agent", industries[0], "98%", "Stock accuracy"),
            ("Automating RFP Response for a Logistics Leader", industries[1], "3.2x", "Faster responses"),
            ("Fraud Triage Copilot for a Regional Bank", industries[2], "-40%", "False positives"),
            ("Clinical Document Extraction at Scale", industries[3], "12x", "Throughput"),
        ]
        out = []
        for i, (title, industry, metric_value, metric_label) in enumerate(studies):
            slug = slugify(title)
            obj, created = CaseStudy.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title,
                    excerpt=f"{PLACEHOLDER} {title} — excerpt for cards.",
                    body=f"<p>{PLACEHOLDER} Full body for {title}.</p>",
                    client_name=f"{PLACEHOLDER} Client {i + 1}",
                    client_anonymous=(i % 2 == 0),
                    industry=industry,
                    challenge=f"<p>{PLACEHOLDER} What the client was up against.</p>",
                    approach=f"<p>{PLACEHOLDER} What we built and why.</p>",
                    outcome=f"<p>{PLACEHOLDER} What changed as a result.</p>",
                    author=team[i % len(team)] if team else None,
                    featured=(i < 3),
                    status=CaseStudy.Status.PUBLISHED, published_at=days_ago(40 - i * 5),
                ),
            )
            if created:
                obj.services.set(random.sample(services, k=min(2, len(services))))
                obj.tech_stack.set(random.sample(tags, k=min(3, len(tags))))
                set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"case-{slug}-hero")
                obj.hero_alt = title
                obj.save()
                stats = [
                    (metric_value, metric_label),
                    (f"{6 + i}wk", "Time to production"),
                    (f"{2 + i}x", "ROI in year one"),
                    (f"{80 + i}%", "Adoption after rollout"),
                ]
                for order, (value, label) in enumerate(stats):
                    Metric.objects.get_or_create(
                        case_study=obj, label=label,
                        defaults=dict(value=value, order=order),
                    )
            out.append(obj)
        return out

    def _seed_blog_posts(self, industries, services, tags, team):
        titles = [
            "Why Agentic AI Needs Human-in-the-Loop Design",
            "Evaluating LLM Agents in Production",
            "RAG vs Fine-Tuning: Picking the Right Tool",
            "What AI Readiness Actually Looks Like",
            "Cutting Latency in Multi-Agent Pipelines",
            "The Real Cost of a Bad AI Rollout",
        ]
        for i, title in enumerate(titles):
            slug = slugify(title)
            obj, created = BlogPost.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title,
                    excerpt=f"{PLACEHOLDER} Excerpt for {title}.",
                    body=f"<p>{PLACEHOLDER} Full body for {title}.</p>",
                    author=team[i % len(team)] if team else None,
                    reading_minutes=4 + i,
                    featured=(i < 2),
                    status=BlogPost.Status.PUBLISHED, published_at=days_ago(i * 6 + 2),
                ),
            )
            if created:
                obj.industries.set(random.sample(industries, k=2))
                obj.related_services.set(random.sample(services, k=2))
                obj.tags.set(random.sample(tags, k=min(2, len(tags))))
                set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"blog-{slug}-hero")
                obj.hero_alt = title
                obj.save()

    def _seed_handbooks(self, tags, team):
        handbooks = [
            ("The AI Readiness Handbook", True),
            ("A Field Guide to Agent Evaluation", False),
        ]
        for i, (title, gated) in enumerate(handbooks):
            slug = slugify(title)
            obj, created = Handbook.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title,
                    excerpt=f"{PLACEHOLDER} Excerpt for {title}.",
                    body=f"<p>{PLACEHOLDER} Full body for {title}.</p>",
                    author=team[i % len(team)] if team else None,
                    page_count=24 + i * 8,
                    gated=gated,
                    status=Handbook.Status.PUBLISHED, published_at=days_ago(i * 10 + 5),
                ),
            )
            if created:
                obj.tags.set(random.sample(tags, k=min(2, len(tags))))
                set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"handbook-{slug}-hero")
                set_placeholder(obj, "cover_image", 600, 800, title, slug=f"handbook-{slug}-cover")
                obj.hero_alt = title
                if not obj.pdf:
                    obj.pdf.save(
                        f"{slug}.pdf",
                        ContentFile(b"%PDF-1.4\n%[Placeholder] demo PDF\n"),
                        save=False,
                    )
                obj.save()

    def _seed_webinars(self, team, tags):
        webinars = [
            ("Live: Designing Agent Guardrails", days_from_now(14), None, "https://example.com/register/agent-guardrails"),
            ("On Demand: Scaling RAG in Production", days_ago(20), "https://example.com/recordings/scaling-rag", ""),
        ]
        for i, (title, starts_at, recording_url, registration_url) in enumerate(webinars):
            slug = slugify(title)
            obj, created = Webinar.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title,
                    excerpt=f"{PLACEHOLDER} Excerpt for {title}.",
                    body=f"<p>{PLACEHOLDER} Full body for {title}.</p>",
                    author=team[i % len(team)] if team else None,
                    starts_at=starts_at,
                    duration_minutes=45,
                    guest_presenters=f"{PLACEHOLDER} Guest Speaker",
                    registration_url=registration_url or "",
                    recording_url=recording_url or "",
                    status=Webinar.Status.PUBLISHED, published_at=days_ago(25),
                ),
            )
            if created:
                if team:
                    obj.presenters.set([team[i % len(team)]])
                obj.tags.set(random.sample(tags, k=min(2, len(tags))))
                set_placeholder(obj, "hero_image", 1200, 675, title, slug=f"webinar-{slug}-hero")
                obj.hero_alt = title
                obj.save()

    # ------------------------------------------------------------ marketing

    def _seed_testimonials(self, case_studies):
        entries = [
            ("Jordan Blake", "VP Operations", "Northwind Retail", True, False),
            ("Casey Nguyen", "Director of Engineering", "Meridian Logistics", True, True),
            ("Amara Okafor", "Chief Data Officer", "Union Financial", False, False),
            ("Liam Fitzgerald", "Head of Product", "Beacon Health", False, False),
            ("Elena Petrova", "COO", "Forge Manufacturing", False, False),
            ("Ravi Deshpande", "VP Strategy", "Atlas Consulting", False, False),
        ]
        for i, (name, role, company, featured, has_video) in enumerate(entries):
            obj, created = Testimonial.objects.get_or_create(
                author_name=name, company=company,
                defaults=dict(
                    quote=f"{PLACEHOLDER} Quote from {name} at {company}.",
                    author_role=role,
                    source_platform=list(Testimonial.SourcePlatform)[i % len(Testimonial.SourcePlatform)],
                    rating=4.5 + (0.5 if i % 2 else 0),
                    case_study=case_studies[i % len(case_studies)] if case_studies else None,
                    featured=featured, order=i,
                ),
            )
            if created:
                set_placeholder(obj, "avatar", 200, 200, name.split()[0], slug=f"testimonial-{i}-avatar")
                if has_video:
                    obj.video_url = "https://example.com/videos/testimonial.mp4"
                    set_placeholder(obj, "video_thumbnail", 800, 450, name, slug=f"testimonial-{i}-video")
                obj.save()

    def _seed_partners(self):
        names = ["AWS", "OpenAI", "Anthropic", "Databricks", "Snowflake", "Microsoft Azure"]
        for i, name in enumerate(names):
            obj, created = Partner.objects.get_or_create(
                name=name, defaults=dict(order=i, active=True),
            )
            if created:
                set_placeholder(obj, "logo", 160, 80, name, slug=f"partner-{slugify(name)}")
                obj.save()

    def _seed_process_steps(self):
        steps = [
            ("Discovery", f"{PLACEHOLDER} Scope the problem and the data."),
            ("Pilot", f"{PLACEHOLDER} Ship a narrow, measurable pilot fast."),
            ("Build", f"{PLACEHOLDER} Harden the pilot into production."),
            ("Rollout", f"{PLACEHOLDER} Roll out with change management."),
            ("Support", f"{PLACEHOLDER} Monitor, retrain, and support."),
        ]
        for i, (title, desc) in enumerate(steps):
            obj, created = ProcessStep.objects.get_or_create(
                title=title, defaults=dict(description=desc, order=i),
            )
            if created:
                set_placeholder(obj, "icon", 64, 64, str(i + 1), slug=f"process-{slugify(title)}")
                obj.save()

    def _seed_engagement_models(self):
        models = [
            ("Fixed Price", f"{PLACEHOLDER} Defined scope, defined price."),
            ("Time & Materials", f"{PLACEHOLDER} Flexible scope, billed by the hour."),
            ("Dedicated Team", f"{PLACEHOLDER} An embedded team, fully yours."),
            ("Hybrid", f"{PLACEHOLDER} A mix suited to your roadmap."),
        ]
        for i, (title, desc) in enumerate(models):
            obj, created = EngagementModel.objects.get_or_create(
                title=title, defaults=dict(description=desc, order=i),
            )
            if created:
                set_placeholder(obj, "icon", 64, 64, str(i + 1), slug=f"engagement-{slugify(title)}")
                obj.save()

    def _seed_comparison_table(self):
        table, created = ComparisonTable.objects.get_or_create(
            title=f"{PLACEHOLDER} Us vs. freelancers vs. agencies",
            defaults=dict(
                intro=f"{PLACEHOLDER} Why teams choose us over the alternatives.",
                column_1_label="Freelancers", column_2_label="Traditional agencies",
                column_3_label="Us", active=True,
            ),
        )
        if created:
            rows = [
                ("Production-grade delivery", "Varies", "Sometimes", "Always"),
                ("Dedicated AI specialists", "Rarely", "Sometimes", "Always"),
                ("Fixed-scope pricing options", "Rarely", "Sometimes", "Always"),
                ("Post-launch support", "Rarely", "Add-on", "Included"),
                ("Time to first pilot", "Varies", "8-12 weeks", "2-4 weeks"),
                ("Governance & evals built in", "Rarely", "Rarely", "Always"),
            ]
            for order, (criterion, c1, c2, c3) in enumerate(rows):
                ComparisonRow.objects.get_or_create(
                    table=table, criterion=criterion,
                    defaults=dict(column_1_value=c1, column_2_value=c2, column_3_value=c3, order=order),
                )

    def _seed_faqs(self, services):
        faqs = [
            (FAQ.Placement.HOME, "How quickly can we start a pilot?", f"{PLACEHOLDER} Typically 2-4 weeks."),
            (FAQ.Placement.HOME, "Do you work with our existing data stack?", f"{PLACEHOLDER} Yes, we integrate rather than replace."),
            (FAQ.Placement.SERVICES, "What does a typical engagement include?", f"{PLACEHOLDER} Discovery, pilot, rollout, support."),
            (FAQ.Placement.SERVICES, "Can you work within our compliance requirements?", f"{PLACEHOLDER} Yes, we design for your governance model."),
            (FAQ.Placement.HIRE, "How fast can a hire start?", f"{PLACEHOLDER} Most engagements start within two weeks."),
            (FAQ.Placement.HIRE, "Are hires dedicated or shared?", f"{PLACEHOLDER} Dedicated, full-time on your engagement."),
            (FAQ.Placement.CONTACT, "What happens after I submit the form?", f"{PLACEHOLDER} We respond within one business day."),
            (FAQ.Placement.CONTACT, "Do you sign NDAs before scoping calls?", f"{PLACEHOLDER} Yes, on request."),
            (FAQ.Placement.GENERAL, "Where are you based?", f"{PLACEHOLDER} San Francisco and London, working globally."),
            (FAQ.Placement.GENERAL, "Do you offer fixed-price engagements?", f"{PLACEHOLDER} Yes, see our engagement models."),
        ]
        for i, (placement, question, answer) in enumerate(faqs):
            FAQ.objects.get_or_create(
                question=question,
                defaults=dict(
                    answer=answer, placement=placement,
                    service=services[i % len(services)] if placement == FAQ.Placement.SERVICES else None,
                    order=i, active=True,
                ),
            )

    # -------------------------------------------------------------- careers

    def _seed_job_postings(self):
        postings = [
            ("Senior AI Agent Engineer", "Engineering", JobPosting.WorkMode.REMOTE, JobPosting.EmploymentType.FULL_TIME),
            ("ML Platform Engineer", "Engineering", JobPosting.WorkMode.HYBRID, JobPosting.EmploymentType.FULL_TIME),
            ("Client Delivery Lead", "Delivery", JobPosting.WorkMode.REMOTE, JobPosting.EmploymentType.CONTRACT),
        ]
        for i, (title, dept, work_mode, employment_type) in enumerate(postings):
            slug = slugify(title)
            JobPosting.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    title=title, department=dept, location="Remote (US/EU)",
                    work_mode=work_mode, employment_type=employment_type,
                    experience_min_years=3 + i, experience_max_years=7 + i,
                    summary=f"{PLACEHOLDER} Summary for {title}.",
                    responsibilities=f"<p>{PLACEHOLDER} Responsibilities for {title}.</p>",
                    requirements=f"<p>{PLACEHOLDER} Requirements for {title}.</p>",
                    nice_to_have=f"<p>{PLACEHOLDER} Nice to have for {title}.</p>",
                    benefits=f"<p>{PLACEHOLDER} Benefits for {title}.</p>",
                    is_open=True, apply_email="careers@example.com",
                    status=JobPosting.Status.PUBLISHED, published_at=days_ago(5 + i),
                ),
            )

    # ---------------------------------------------------------------- pages

    def _seed_site_settings(self):
        settings_obj = SiteSettings.load()
        if not settings_obj.site_name:
            settings_obj.site_name = "NeuroML.ai"
            settings_obj.email = "hello@example.com"
            settings_obj.phone = "+1 555 0100"
            settings_obj.whatsapp_number = "+15550100"
            settings_obj.whatsapp_prefill = f"{PLACEHOLDER} Hi, I'd like to talk about a project."
            settings_obj.linkedin_url = "https://linkedin.com/company/example"
            settings_obj.twitter_url = "https://x.com/example"
            set_placeholder(settings_obj, "favicon", 64, 64, "AI", slug="site-favicon")
            set_placeholder(settings_obj, "default_og_image", 1200, 630, "AI Consultancy", slug="site-og")
            settings_obj.save()

    def _seed_homepage(self):
        home = HomePage.load()
        if not home.hero_heading:
            # Two-tone heading: two_tone_heading.html splits on newlines and
            # mutes line 2 — that's the "grey half" of the treatment.
            home.hero_heading = "AI that ships.\nNot AI that demos."
            home.hero_subheading = (
                "Most AI pilots never reach production. We build the ones "
                "that do — agents, retrieval systems, and vision models "
                "running against real users and real data."
            )
            home.hero_cta_label = "Tell us what's stuck"
            home.hero_cta_url = "/contact/"
            home.expertise_heading = "Three things, done properly"
            home.expertise_intro = f"{PLACEHOLDER} Intro copy for the expertise section."
            home.use_cases_heading = "Where this actually gets used"
            home.case_studies_heading = "Work that made it to production"
            home.insights_heading = "Notes from the build"
            set_placeholder(home, "hero_image", 1200, 900, "Hero", slug="home-hero")
            home.save()

    def _seed_lead_popup(self, recognitions):
        popup = LeadPopup.load()
        if not popup.heading:
            popup.heading = f"{PLACEHOLDER} Let's talk about your AI roadmap"
            popup.subheading = f"{PLACEHOLDER} A free 30-minute strategy call."
            popup.footer_text = f"{PLACEHOLDER} No spam, just a real conversation."
            popup.form_heading = "Get in touch"
            popup.submit_label = "Send"
            popup.success_message = f"{PLACEHOLDER} Thanks — we'll be in touch shortly."
            popup.delay_seconds = 60
            popup.frequency_days = 1
            popup.show_on_mobile = False
            popup.hide_after_submit_days = 90
            popup.exclude_paths = "/contact/\n/book-a-demo/"
            set_placeholder(popup, "panel_image", 600, 800, "Popup", slug="popup-panel")
            popup.save()
            popup.badges.set(recognitions[:3])
            steps = [
                "Free 30-minute strategy call",
                "No obligation, no pressure",
                "Talk to a real engineer, not a salesperson",
            ]
            for order, text in enumerate(steps):
                PopupStep.objects.get_or_create(popup=popup, text=text, defaults={"order": order})
