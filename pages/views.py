"""The preview capability: a signed, time-limited token lets a logged-in
staff member view an unpublished object. Every detail view already has its
own staff `?preview=1` bypass (see e.g. solutions.views), so this just
verifies the token and hands off to the object's real detail page with that
flag set — there's no separate preview template to maintain.
"""

from itertools import chain, groupby

from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.utm import utm_initial
from insights.models import BlogPost, CaseStudy, Handbook
from marketing.forms import ContactForm
from marketing.models import (
    ClientLogo, ComparisonTable, EngagementModel, FAQ, Partner, ProcessStep,
    Testimonial,
)
from pages.models import HomePage, Office
from people.models import TeamMember
from solutions.models import Service, Technology, UseCase
from taxonomy.models import Industry, ServiceCluster

PREVIEW_SALT = "pages.preview"
PREVIEW_MAX_AGE = 60 * 60 * 24  # 24 hours

# The hero card stack — a curated capability overview, not a live Service
# queryset: six fixed labels chosen for the hero specifically, including
# iGaming/Full-Stack framing that doesn't map 1:1 onto real service titles.
HERO_CAPABILITIES = [
    "AI Agents & Automation",
    "RAG & Knowledge Systems",
    "Computer Vision",
    "iGaming Platforms",
    "Full-Stack Product",
    "ML Engineering",
]


def _homepage_use_cases():
    homepage_use_cases = (
        UseCase.objects.live()
        .filter(show_on_homepage=True)
        .select_related("industry")
        .order_by("industry__order", "order")
    )
    return [
        {"industry": industry, "use_cases": list(cases)}
        for industry, cases in groupby(homepage_use_cases, key=lambda uc: uc.industry)
    ]


def _homepage_stats(home_page):
    """First three are always derived live — never stored, never stale.
    The fourth has no database source, so it's the one editable field on
    HomePage; omitted entirely (not a placeholder) when blank. See
    pages/models.py's comment on stat_4_value for why."""
    stats = [
        {"value": CaseStudy.objects.live().count(), "label": "Published case studies"},
        {
            "value": CaseStudy.objects.live()
            .filter(industry__slug="igaming-sweepstakes").count(),
            "label": "Live iGaming platforms",
        },
        {"value": Technology.objects.live().count(), "label": "Technologies"},
    ]
    if home_page.stat_4_value:
        stats.append({"value": home_page.stat_4_value, "label": home_page.stat_4_label})
    return stats


def home(request):
    home_page = HomePage.load()
    use_cases_by_industry = _homepage_use_cases()

    case_studies = (
        CaseStudy.objects.live()
        .filter(featured=True)
        .select_related("industry")
        .prefetch_related("metrics")[:8]
    )

    insights = sorted(
        chain(
            BlogPost.objects.live().select_related("author")[:4],
            Handbook.objects.live()[:2],
        ),
        key=lambda item: item.published_at,
        reverse=True,
    )[:4]

    comparison_table = (
        ComparisonTable.objects.filter(active=True)
        .prefetch_related("rows")
        .first()
    )

    context = {
        "home": home_page,
        "seo": home_page,
        "tech_partners": Partner.objects.filter(active=True).order_by("order"),
        "service_clusters": ServiceCluster.objects.order_by("order").prefetch_related(
            Prefetch(
                "services",
                queryset=Service.objects.live().order_by("order"),
            )
        ),
        "industry_use_cases": use_cases_by_industry,
        "initial_use_cases": (
            use_cases_by_industry[0]["use_cases"] if use_cases_by_industry else []
        ),
        "featured_case_studies": case_studies,
        "insights": insights,
        "testimonials": Testimonial.objects.filter(featured=True).order_by("order")[:6],
        "client_logos": ClientLogo.objects.filter(active=True).order_by("order"),
        "process_steps": ProcessStep.objects.order_by("order")[:5],
        "comparison_table": comparison_table,
        # Deliberately not .live() — the stack grid is a logo badge, not a
        # link into content, so a technology can be featured here even while
        # its own detail page is unpublished. See tech_stack card markup.
        "tech_stack": Technology.objects.filter(show_in_stack_grid=True)
        .order_by("order"),
        "home_faqs": FAQ.objects.filter(placement=FAQ.Placement.HOME, active=True).order_by("order"),
        "contact_form": ContactForm(initial=utm_initial(request)),
        "stats": _homepage_stats(home_page),
        "hero_capabilities": HERO_CAPABILITIES,
    }
    return render(request, "pages/home.html", context)


def home_industry_panel(request, slug):
    """HTMX endpoint backing the homepage's industry-tabbed use cases.

    Returns just the panel markup so switching tabs never reloads the page.
    """
    industry = get_object_or_404(Industry, slug=slug)
    use_cases = (
        UseCase.objects.live()
        .filter(show_on_homepage=True, industry=industry)
        .order_by("order")
    )
    return render(request, "pages/_home_industry_panel.html", {"use_cases": use_cases})


def about(request):
    context = {
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "About", "url": None},
        ],
        "team_members": TeamMember.objects.filter(show_on_about=True).order_by("order"),
        "process_steps": ProcessStep.objects.order_by("order")[:5],
        "engagement_models": EngagementModel.objects.order_by("order"),
        "offices": Office.objects.order_by("order"),
    }
    return render(request, "pages/about.html", context)


def contact(request):
    context = {
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Contact", "url": None},
        ],
        "offices": Office.objects.order_by("order"),
        "form": ContactForm(initial=utm_initial(request)),
    }
    return render(request, "pages/contact.html", context)


def privacy(request):
    context = {
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Privacy policy", "url": None},
        ],
    }
    return render(request, "pages/privacy.html", context)


def terms(request):
    context = {
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Terms of service", "url": None},
        ],
    }
    return render(request, "pages/terms.html", context)


def make_preview_token(obj):
    content_type = ContentType.objects.get_for_model(obj)
    return signing.dumps({"ct": content_type.pk, "pk": obj.pk}, salt=PREVIEW_SALT)


def preview(request, token):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise PermissionDenied

    try:
        data = signing.loads(token, salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE)
    except signing.BadSignature as exc:
        raise Http404 from exc

    content_type = get_object_or_404(ContentType, pk=data["ct"])
    obj = get_object_or_404(content_type.model_class(), pk=data["pk"])
    if not hasattr(obj, "get_absolute_url"):
        raise Http404
    return redirect(f"{obj.get_absolute_url()}?preview=1")
