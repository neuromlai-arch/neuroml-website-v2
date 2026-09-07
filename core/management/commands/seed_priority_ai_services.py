"""Seeds the three priority AI service pages missing from the AI & Machine
Learning cluster (see the site audit: 5 of the 9 target AI service pages
were published, these were the highest-priority gap) — AI Consulting &
Strategy, Generative AI Development, and Machine Learning Development.

Idempotent: each Service/FAQ is keyed via get_or_create and every field is
re-applied on every run, same pattern as seed_igaming.py.

Created as REVIEW, not PUBLISHED, deliberately — this is new marketing copy
that should get a human read-through before it goes live on an indexed page.
Publish each one from the admin once reviewed.

No Technology rows are attached here: Technology.slug is globally unique
(one row per tool, owned by a single service), so "OpenAI API" already
belongs to llm-application-development and "PyTorch" to computer-vision —
attaching them again under a new slug would just duplicate the same tool
under two card labels. The relevant tools are named in body copy instead.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Publishable
from marketing.models import FAQ
from solutions.models import Service
from taxonomy.models import ServiceCluster

SERVICES = [
    dict(
        slug="ai-consulting-strategy",
        title="AI Consulting & Strategy",
        order=5,
        tagline="A clear technical read on where AI is worth building — before you commit a team to it.",
        summary=(
            "Structured technical assessment of your systems and data to find where AI is "
            "worth building, sized as a pilot that proves the case in weeks rather than a "
            "roadmap that promises results in a year."
        ),
        meta_title="AI Consulting & Strategy Services | NeuroML.AI",
        meta_description=(
            "Technical AI assessment and a build plan for your team — where AI is worth "
            "building, sized as a pilot with a clear success criterion agreed up front."
        ),
        body=(
            "<p>Most AI initiatives stall before they start — not from a shortage of ideas, "
            "but from nobody having scoped a pilot small enough to prove or disprove the "
            "case in weeks. We run a structured assessment of your systems, data and "
            "workflows, and come back with a small number of opportunities ranked by "
            "expected value against build cost, not a long list of things AI could "
            "theoretically touch.</p>"
            "<p>The output is a technical roadmap, not a slide deck: a scoped pilot for the "
            "highest-value opportunity, the data and access it needs, a success criterion "
            "you agree to before we start, and a realistic view of what production would "
            "take if the pilot works. Where the honest answer is “not yet” — "
            "the data isn't there, the workflow isn't stable enough, the cost of being "
            "wrong is too high for current model quality — we say so.</p>"
            "<p>Typical engagements include:</p>"
            "<ul>"
            "<li><strong>Opportunity mapping</strong> — a structured pass over your "
            "workflows to find where AI genuinely reduces cost or does something manual "
            "work can't do at the same speed.</li>"
            "<li><strong>Feasibility and data readiness</strong> — checking whether the "
            "data, systems access and volume actually support the use case before any code "
            "is written.</li>"
            "<li><strong>Build vs. buy</strong> — an honest comparison against existing "
            "tools and APIs, since not every problem needs a custom system.</li>"
            "<li><strong>Pilot scoping</strong> — a fixed-scope pilot with a defined "
            "success metric, sized to answer the question in weeks rather than a quarter.</li>"
            "<li><strong>Architecture review</strong> — for teams with an AI system "
            "already in progress that's stalled or about to be scaled.</li>"
            "</ul>"
            "<p>This is usually the starting point for a longer relationship — the "
            "pilot either earns a production build, or it saves a much larger build that "
            "wouldn't have worked. We work with teams anywhere from early-stage product "
            "companies deciding whether to build an AI feature at all, to established "
            "businesses that want a second opinion before committing an engineering team "
            "to an AI roadmap.</p>"
        ),
        faqs=[
            (
                "How is this different from just building the pilot yourselves?",
                "<p>It usually leads straight into a pilot — the assessment exists so "
                "the pilot is scoped correctly the first time, with a success criterion "
                "agreed before any code is written, rather than discovering three weeks in "
                "that the data isn't there or the assumptions were wrong.</p>",
            ),
            (
                "What if the answer is that AI isn't worth it for us right now?",
                "<p>That's a valid outcome, and we'll tell you if that's what we find. "
                "Rushing a low-value use case into production usually costs more than the "
                "assessment does — it's cheaper to find out early.</p>",
            ),
            (
                "How long does an assessment take?",
                "<p>Typically one to three weeks, depending on how many workflows are in "
                "scope and how quickly we can get access to the relevant systems and "
                "data.</p>",
            ),
            (
                "Do you require a long-term contract to start?",
                "<p>No. The assessment and any resulting pilot are scoped and priced on "
                "their own — whether it leads to a larger engagement depends on what "
                "the pilot proves.</p>",
            ),
        ],
    ),
    dict(
        slug="generative-ai-development",
        title="Generative AI Development",
        order=6,
        tagline=(
            "Generative features built into your product — content, personalization and "
            "structured output backed by evaluation, not a prompt wired to an API key."
        ),
        summary=(
            "We build generative AI features into existing products — content generation, "
            "personalization and structured output — grounded in your data and evaluated "
            "against a real quality bar before they ship."
        ),
        meta_title="Generative AI Development Company | NeuroML.AI",
        meta_description=(
            "Generative AI features built into your product — content generation, "
            "structured output and personalization, evaluated before they ship."
        ),
        body=(
            "<p>A demo that generates convincing text is easy. A generation feature your "
            "product can ship — with consistent quality, guardrails against off-brand "
            "or incorrect output, and a way to catch regressions before users do — is "
            "the actual engineering problem. We build the generation layer as a product "
            "feature: prompted, evaluated and monitored like any other part of your system, "
            "not a one-off script wired to an API key.</p>"
            "<p>This covers generative features embedded directly in a product, as opposed "
            "to information-retrieval applications like search or document Q&amp;A (see "
            "<a href=\"/services/llm-application-development/\">LLM Application "
            "Development</a>) or agents that take multi-step action (see "
            "<a href=\"/services/ai-agents-automation/\">AI Agents &amp; Automation</a>) "
            "— though the three often sit in the same system.</p>"
            "<p>Work in this area typically includes:</p>"
            "<ul>"
            "<li><strong>Content generation</strong> — product descriptions, listings, "
            "summaries or copy variants your product generates at scale rather than a "
            "person writing each one.</li>"
            "<li><strong>Structured generation</strong> — output constrained to a "
            "schema your application can consume directly, not free text you have to parse "
            "and hope is well-formed.</li>"
            "<li><strong>Personalization</strong> — generated content shaped by a "
            "user's own data or history, rather than the same output for every user.</li>"
            "<li><strong>Prompt and output evaluation</strong> — a test set and "
            "scoring approach that catches quality regressions before a prompt or model "
            "change ships, not after users notice.</li>"
            "<li><strong>Model selection and fallback</strong> — choosing the right "
            "model for cost and latency per feature, with a fallback path when a provider "
            "is degraded or a response fails validation.</li>"
            "</ul>"
            "<p>The result is a feature that behaves predictably in production: bounded "
            "output, monitored quality, and a clear path to improve it once it's live "
            "rather than a fixed prompt nobody wants to touch again.</p>"
        ),
        faqs=[
            (
                "How do you keep generated output on-brand and factually safe?",
                "<p>Through constrained prompting, output validation against a schema or "
                "rule set, and an evaluation set you review before launch — the same "
                "quality bar you'd hold a human writer to, checked automatically on every "
                "change.</p>",
            ),
            (
                "Can this work with our existing product and database, or does it need to "
                "be a new system?",
                "<p>It's built as a feature inside your existing product and data, not a "
                "separate tool. Integration is usually an API layer your application "
                "already calls, backed by your own data rather than a generic public "
                "model.</p>",
            ),
            (
                "Which AI providers do you build on?",
                "<p>Primarily OpenAI and Anthropic's APIs, chosen per feature based on "
                "cost, latency and output quality for that specific task — we don't "
                "lock a whole product to a single provider by default.</p>",
            ),
            (
                "How do you catch quality regressions after launch?",
                "<p>An evaluation set runs against every prompt or model change before it "
                "ships, and production output is sampled and monitored on an ongoing basis "
                "so a quality drop is caught by a dashboard, not a support ticket.</p>",
            ),
        ],
    ),
    dict(
        slug="machine-learning-development",
        title="Machine Learning Development",
        order=7,
        tagline=(
            "Models built and validated against your data — classification, forecasting and "
            "recommendation systems that hold up outside the training set."
        ),
        summary=(
            "We build and validate the models themselves — classification, forecasting, "
            "recommendation and other predictive systems — trained and tested against your "
            "real data, not a benchmark dataset."
        ),
        meta_title="Machine Learning Development Services | NeuroML.AI",
        meta_description=(
            "Custom machine learning models — classification, forecasting and "
            "recommendation systems — built and validated against your own data, not a "
            "public benchmark."
        ),
        body=(
            "<p>Before a model can be deployed or monitored, it has to be built — "
            "framed as the right prediction problem, trained on the right features, and "
            "validated in a way that actually predicts how it will perform on new data "
            "rather than data it's already seen. That's what this covers: the model "
            "itself, not the infrastructure around it (see "
            "<a href=\"/services/ml-engineering-mlops/\">ML Engineering &amp; MLOps</a> "
            "for deployment, monitoring and retraining pipelines).</p>"
            "<p>We work from your existing data — transactional, behavioral, "
            "operational, whatever your business already generates — rather than "
            "treating a public benchmark as a stand-in for your problem. A model that "
            "scores well on a leaderboard and poorly on your actual customers hasn't "
            "solved anything.</p>"
            "<p>Typical engagements include:</p>"
            "<ul>"
            "<li><strong>Classification and scoring models</strong> — fraud risk, "
            "churn likelihood, lead quality, and similar problems where the output is a "
            "category or a score.</li>"
            "<li><strong>Forecasting and demand prediction</strong> — time-series "
            "models for demand, inventory, staffing or revenue projections.</li>"
            "<li><strong>Recommendation systems</strong> — ranking and personalization "
            "built on your own catalogue and user behavior rather than a generic "
            "collaborative-filtering template.</li>"
            "<li><strong>Feature engineering and data validation</strong> — turning "
            "raw operational data into inputs a model can actually learn from, and "
            "catching leakage before it inflates a validation score.</li>"
            "<li><strong>Model evaluation</strong> — validation methodology matched "
            "to the problem (holdout, time-based split, cross-validation), plus the "
            "business-relevant metrics, not accuracy alone.</li>"
            "</ul>"
            "<p>We hand off a model that's been validated against a realistic split of "
            "your own data, documented well enough for your team to retrain it, and — "
            "where you want it — plugged into the deployment and monitoring work "
            "under ML Engineering &amp; MLOps.</p>"
        ),
        faqs=[
            (
                "Do you need a data science team on our side already?",
                "<p>No. We can work from raw operational data and build the pipeline "
                "needed to get it into a trainable state — though if you have an "
                "existing data or analytics team, we work directly with them rather than "
                "around them.</p>",
            ),
            (
                "How do you know a model will hold up on new data, not just the training "
                "set?",
                "<p>Through validation methodology matched to the problem — a "
                "time-based split for anything sequential, holdout sets that mirror how "
                "the model will actually be used, and business-relevant metrics rather "
                "than accuracy alone.</p>",
            ),
            (
                "Can you take an existing model we built and improve it?",
                "<p>Yes — this is common. We start by validating the existing model "
                "against a proper holdout to understand where it's actually "
                "underperforming before changing anything.</p>",
            ),
            (
                "What happens after the model is built?",
                "<p>Deployment, monitoring and retraining are handled separately, under "
                "ML Engineering &amp; MLOps — we hand off a validated, documented "
                "model ready for that step, or run both as one engagement if you'd rather "
                "not manage the handoff.</p>",
            ),
        ],
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds AI Consulting & Strategy, Generative AI Development and Machine Learning "
        "Development as REVIEW-status Service pages. Publish each from the admin once "
        "reviewed."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        cluster = ServiceCluster.objects.get(name="AI & Machine Learning")

        for entry in SERVICES:
            service, created = Service.objects.get_or_create(
                slug=entry["slug"],
                defaults={"cluster": cluster, "status": Publishable.Status.REVIEW},
            )
            service.cluster = cluster
            service.title = entry["title"]
            service.tagline = entry["tagline"]
            service.summary = entry["summary"]
            service.body = entry["body"]
            service.meta_title = entry["meta_title"]
            service.meta_description = entry["meta_description"]
            service.order = entry["order"]
            service.show_in_nav = True
            service.show_in_form_dropdown = True
            if service.status == Publishable.Status.DRAFT:
                service.status = Publishable.Status.REVIEW
            service.save()

            for question, answer in entry["faqs"]:
                FAQ.objects.update_or_create(
                    service=service,
                    question=question,
                    defaults={
                        "answer": answer,
                        "placement": FAQ.Placement.SERVICES,
                        "active": True,
                    },
                )

            self.stdout.write(
                self.style.SUCCESS(f"{'created' if created else 'updated'}: {service.slug}")
            )

        self.stdout.write(self.style.SUCCESS(
            "Done. All three are status=review — read them over in /manage/ and publish "
            "when ready."
        ))
