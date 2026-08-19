"""The preview capability: a signed, time-limited token lets a logged-in
staff member view an unpublished object. No template exists for any content
type yet (session 2) — this renders the same stub as the real detail URLs.
"""

from itertools import chain, groupby

from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render

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


def home(request):
    home_page = HomePage.load()
    use_cases_by_industry = _homepage_use_cases()

    case_studies = (
        CaseStudy.objects.live()
        .filter(featured=True)
        .select_related("industry")
        .prefetch_related("metrics")[:3]
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
        "hero_services": Service.objects.live().order_by("cluster__order", "order")[:3],
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
        "tech_stack": Technology.objects.live()
        .filter(show_in_stack_grid=True)
        .order_by("order"),
        "home_faqs": FAQ.objects.filter(placement=FAQ.Placement.HOME, active=True).order_by("order"),
        "contact_form": ContactForm(initial=utm_initial(request)),
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
    return render(request, "stub_detail.html", {"object": obj, "is_preview": True})
