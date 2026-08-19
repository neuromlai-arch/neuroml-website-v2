from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from insights.models import CaseStudy
from taxonomy.models import Industry


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
    breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Industries", "url": "/industries/"},
        {"label": industry.name, "url": None},
    ]
    return render(
        request, "taxonomy/industry_detail.html",
        {
            "object": industry,
            "use_cases": use_cases,
            "case_studies": case_studies,
            "products": products,
            "breadcrumbs": breadcrumbs,
        },
    )
