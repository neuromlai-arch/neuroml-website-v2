"""Seeds the AboutPage singleton with the copy that was hardcoded directly
in templates/pages/about.html — moving it into the model shouldn't change
anything a visitor sees, just where an editor goes to change it.

Historical models from `apps.get_model` don't carry SingletonModel's custom
save() (migrations only reconstruct fields, not methods), so pk=1 is set
explicitly here rather than relying on that override.
"""

from django.db import migrations

HEADING = "Engineers who ship, not consultants who advise"

INTRO_PARAGRAPH_1 = (
    "We're an AI engineering studio. We build agents, retrieval systems and "
    "vision models that run in production against real users and real data "
    "— and the software around them, because an AI feature is a small part "
    "of a working product."
)
INTRO_PARAGRAPH_2 = (
    "Most of our work is alongside an in-house team rather than replacing "
    "one. Some of it can't be named publicly, which is why parts of this "
    "site describe work by sector rather than by client."
)

META_TITLE = "About — NeuroML.ai"
META_DESCRIPTION = (
    "An AI engineering studio building agents, retrieval systems and "
    "computer vision that reach production. Six live iGaming platforms and "
    "30 delivered projects."
)

CTA_BODY = (
    "Send us the shape of the problem — the pilot that stalled, the "
    "retrieval that hallucinates, the model that drifted. We'll tell you "
    "honestly whether we're the right people for it."
)

CAPABILITIES = [
    (
        "iGaming platform engineering",
        "Six live betting platforms across Europe and Africa — sportsbook "
        "and casino cores, double-entry wallet ledgers, risk and trading "
        "tooling, and multi-tenant architecture serving several brands from "
        "one codebase.",
    ),
    (
        "Production AI systems",
        "Agents, retrieval systems and computer vision that run against "
        "real users and real data — with the evaluation harnesses, drift "
        "monitoring and cost controls that decide whether they survive past "
        "launch.",
    ),
    (
        "The product around it",
        "Full-stack builds in Python and TypeScript, mobile in React Native "
        "and Flutter, and the cloud infrastructure underneath. An AI "
        "feature is a small part of a working product, and the seam "
        "between two vendors is where projects stall.",
    ),
]

EXPECTATIONS = [
    (
        "We'll tell you when it's not an AI problem",
        "A lot of work described as AI turns out to be a data problem, a "
        "process problem, or a rules engine nobody wanted to write. Finding "
        "that out in the scoping call costs you an hour rather than three "
        "months.",
    ),
    (
        "Evaluation before implementation",
        "The harness that measures a system gets built before the system "
        "does. Without it, there's no way to tell whether a change improved "
        "things or just changed them.",
    ),
    (
        "Honest accuracy figures",
        "A detector at 94% on your data is a useful tool if you know where "
        "the 6% falls. Sold as 99%, it's a liability. We characterise "
        "accuracy by condition rather than reporting one number.",
    ),
    (
        "Handover, not dependency",
        "Documentation written for whoever inherits the system. You should "
        "be able to run, retrain and extend it without us — and if you'd "
        "rather we stayed, that should be a choice.",
    ),
]


def seed_about_page(apps, schema_editor):
    AboutPage = apps.get_model("pages", "AboutPage")
    Capability = apps.get_model("pages", "Capability")
    Expectation = apps.get_model("pages", "Expectation")

    about_page, _ = AboutPage.objects.get_or_create(
        pk=1,
        defaults={
            "heading": HEADING,
            "intro_paragraph_1": INTRO_PARAGRAPH_1,
            "intro_paragraph_2": INTRO_PARAGRAPH_2,
            "cta_body": CTA_BODY,
            "meta_title": META_TITLE,
            "meta_description": META_DESCRIPTION,
        },
    )

    for order, (title, description) in enumerate(CAPABILITIES):
        Capability.objects.get_or_create(
            about_page=about_page, title=title,
            defaults={"description": description, "order": order},
        )

    for order, (title, description) in enumerate(EXPECTATIONS):
        Expectation.objects.get_or_create(
            about_page=about_page, title=title,
            defaults={"description": description, "order": order},
        )


def unseed_about_page(apps, schema_editor):
    AboutPage = apps.get_model("pages", "AboutPage")
    AboutPage.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0006_aboutpage_capability_expectation"),
    ]

    operations = [
        migrations.RunPython(seed_about_page, unseed_about_page),
    ]
