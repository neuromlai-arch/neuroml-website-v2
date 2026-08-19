"""List and detail views for Service, Technology, Product, HireRole.

Mirrors the pattern already established in insights/views.py: list views
render a `#results` partial only for HTMX requests (filters and pagination
both `hx-get` into that target), detail views replicate the staff
`?preview=1` bypass inline rather than depending on core.views.stub_detail.
"""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from marketing.models import FAQ
from solutions.models import HireRole, Product, Service, Technology, UseCase
from taxonomy.models import Industry, ServiceCluster

PAGE_SIZE = 12


def _is_preview(request):
    return (
        request.GET.get("preview") == "1"
        and request.user.is_authenticated
        and request.user.is_staff
    )


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))


def _filters_querystring(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


# ----------------------------------------------------------------- Services

def service_list(request):
    qs = Service.objects.live().select_related("cluster", "parent")
    cluster_slug = request.GET.get("cluster", "")
    if cluster_slug:
        qs = qs.filter(cluster__slug=cluster_slug)

    context = {
        "page_obj": _paginate(request, qs),
        "querystring": _filters_querystring(request),
        "clusters": ServiceCluster.objects.order_by("order"),
        "active_cluster": cluster_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Services", "url": None},
        ],
    }
    template = "solutions/_service_results.html" if _is_htmx(request) else "solutions/service_list.html"
    return render(request, template, context)


def service_detail(request, slug):
    manager = Service.objects if _is_preview(request) else Service.objects.live()
    service = get_object_or_404(
        manager.select_related("cluster", "parent"), slug=slug,
    )
    breadcrumbs = [
        {"label": "Home", "url": reverse("home")},
        {"label": "Services", "url": reverse("service_list")},
    ]
    if service.parent_id:
        breadcrumbs.append({"label": service.parent.title, "url": service.parent.get_absolute_url()})
    breadcrumbs.append({"label": service.title, "url": None})

    context = {
        "object": service,
        "seo": service,
        "children": service.children.live().order_by("order") if not service.parent_id else [],
        "technologies": service.technologies.live().filter(show_in_nav=True).order_by("order"),
        "faqs": FAQ.objects.filter(service=service, active=True).order_by("order"),
        "breadcrumbs": breadcrumbs,
    }
    return render(request, "solutions/service_detail.html", context)


# --------------------------------------------------------------- Technology

def technology_list(request):
    qs = Technology.objects.live().select_related("service")
    service_slug = request.GET.get("service", "")
    if service_slug:
        qs = qs.filter(service__slug=service_slug)

    context = {
        "page_obj": _paginate(request, qs),
        "querystring": _filters_querystring(request),
        "services": Service.objects.live().filter(show_in_nav=True).order_by("order"),
        "active_service": service_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Technologies", "url": None},
        ],
    }
    template = (
        "solutions/_technology_results.html" if _is_htmx(request) else "solutions/technology_list.html"
    )
    return render(request, template, context)


def technology_detail(request, slug):
    manager = Technology.objects if _is_preview(request) else Technology.objects.live()
    technology = get_object_or_404(manager.select_related("service"), slug=slug)
    context = {
        "object": technology,
        "seo": technology,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Technologies", "url": reverse("technology_list")},
            {"label": technology.name, "url": None},
        ],
    }
    return render(request, "solutions/technology_detail.html", context)


# ------------------------------------------------------------------ Products

def product_list(request):
    qs = Product.objects.live().prefetch_related("industries")
    industry_slug = request.GET.get("industry", "")
    if industry_slug:
        qs = qs.filter(industries__slug=industry_slug)

    context = {
        "page_obj": _paginate(request, qs.distinct()),
        "querystring": _filters_querystring(request),
        "industries": Industry.objects.filter(show_in_nav=True),
        "active_industry": industry_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Products", "url": None},
        ],
    }
    template = "solutions/_product_results.html" if _is_htmx(request) else "solutions/product_list.html"
    return render(request, template, context)


def product_detail(request, slug):
    manager = Product.objects if _is_preview(request) else Product.objects.live()
    product = get_object_or_404(manager.prefetch_related("industries"), slug=slug)
    context = {
        "object": product,
        "seo": product,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Products", "url": reverse("product_list")},
            {"label": product.title, "url": None},
        ],
    }
    return render(request, "solutions/product_detail.html", context)


# ----------------------------------------------------------------- Hire roles

def hire_role_list(request):
    qs = HireRole.objects.live().prefetch_related("related_services", "skills")
    service_slug = request.GET.get("service", "")
    if service_slug:
        qs = qs.filter(related_services__slug=service_slug)

    context = {
        "page_obj": _paginate(request, qs.distinct()),
        "querystring": _filters_querystring(request),
        "services": Service.objects.live().filter(show_in_nav=True).order_by("order"),
        "active_service": service_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Hire", "url": None},
        ],
    }
    template = "solutions/_hire_role_results.html" if _is_htmx(request) else "solutions/hire_role_list.html"
    return render(request, template, context)


def hire_role_detail(request, slug):
    manager = HireRole.objects if _is_preview(request) else HireRole.objects.live()
    role = get_object_or_404(
        manager.prefetch_related("skills", "related_services"), slug=slug,
    )
    context = {
        "object": role,
        "seo": role,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Hire", "url": reverse("hire_role_list")},
            {"label": role.title, "url": None},
        ],
    }
    return render(request, "solutions/hire_role_detail.html", context)


# ----------------------------------------------------------------- Use cases

def use_case_list(request):
    qs = UseCase.objects.live().select_related("industry", "related_service")
    industry_slug = request.GET.get("industry", "")
    service_slug = request.GET.get("service", "")
    if industry_slug:
        qs = qs.filter(industry__slug=industry_slug)
    if service_slug:
        qs = qs.filter(related_service__slug=service_slug)

    context = {
        "page_obj": _paginate(request, qs),
        "querystring": _filters_querystring(request),
        "industries": Industry.objects.filter(show_in_nav=True),
        "active_industry": industry_slug,
        "active_service": service_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Use cases", "url": None},
        ],
    }
    template = "solutions/_use_case_results.html" if _is_htmx(request) else "solutions/use_case_list.html"
    return render(request, template, context)


def use_case_detail(request, slug):
    manager = UseCase.objects if _is_preview(request) else UseCase.objects.live()
    use_case = get_object_or_404(manager.select_related("industry", "related_service"), slug=slug)
    context = {
        "object": use_case,
        "seo": use_case,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Industries", "url": reverse("industry_list")},
            {"label": use_case.industry.name, "url": use_case.industry.get_absolute_url()},
            {"label": use_case.title, "url": None},
        ],
    }
    return render(request, "solutions/use_case_detail.html", context)
