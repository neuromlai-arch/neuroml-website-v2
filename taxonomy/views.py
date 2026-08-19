from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from insights.models import CaseStudy
from marketing.models import FAQ
from taxonomy.models import Industry

# These questions were written specifically for the iGaming industry page —
# FAQ has no industry FK (it's a small, deliberately generic model), so this
# is how the industry_detail view scopes 'general' FAQs to this one page
# instead of pulling in every unrelated general-placement FAQ site-wide.
IGAMING_FAQ_QUESTIONS = [
    "Do you build custom platforms or deploy white-label?",
    "What does multi-tenant architecture actually mean here?",
    "What compliance tooling do you provide?",
    "How long does a launch take?",
]


def industry_list(request):
    industries = Industry.objects.filter(show_in_nav=True).order_by("order")
    page_obj = Paginator(industries, 12).get_page(request.GET.get("page"))
    breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Industries", "url": None},
    ]
    return render(
        request, "taxonomy/industry_list.html",
        {"industries": page_obj, "page_obj": page_obj, "breadcrumbs": breadcrumbs},
    )


def industry_detail(request, slug):
    industry = get_object_or_404(Industry, slug=slug)
    use_cases = industry.use_cases.live().order_by("order")
    case_studies = CaseStudy.objects.live().filter(industry=industry).prefetch_related("metrics")[:6]
    products = industry.products.live().order_by("order")
    igaming_faqs = (
        FAQ.objects.filter(
            placement=FAQ.Placement.GENERAL, active=True,
            question__in=IGAMING_FAQ_QUESTIONS,
        ).order_by("order")
        if industry.slug == "igaming-sweepstakes" else FAQ.objects.none()
    )
    breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Industries", "url": "/industries/"},
        {"label": industry.name, "url": None},
    ]
    return render(
        request, "taxonomy/industry_detail.html",
        {
            "object": industry,
            "seo": {
                "seo_title": industry.name,
                "meta_description": industry.blurb,
                "hero_image": industry.icon,
            },
            "use_cases": use_cases,
            "case_studies": case_studies,
            "products": products,
            "igaming_faqs": igaming_faqs,
            "breadcrumbs": breadcrumbs,
        },
    )
