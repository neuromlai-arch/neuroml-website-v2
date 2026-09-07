"""List and detail views for the four insight types.

List views render a `#results` partial only when the request came from HTMX
(filter pills and pagination both `hx-get` into that target), so filtering
and paging never trigger a full page reload. Detail views mirror
`core.views.stub_detail`'s staff `?preview=1` bypass inline, since each type
needs its own `select_related`/`prefetch_related` shape.
"""

from django.core import signing
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import strip_tags
from django_ratelimit.decorators import ratelimit

from core.notifications import notify_staff_of_submission
from core.utm import utm_initial
from insights.models import BlogPost, CaseStudy, Handbook, Webinar
from pages.models import SiteSettings
from solutions.models import UseCase
from taxonomy.models import Industry, Tag

PAGE_SIZE = 12
HANDBOOK_SALT = "insights.handbook_download"
HANDBOOK_DOWNLOAD_MAX_AGE = 60 * 10  # 10 minutes


def _is_preview(request):
    return (
        request.GET.get("preview") == "1"
        and request.user.is_authenticated
        and request.user.is_staff
    )


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))


def _filters_querystring(request):
    """Current querystring with `page` stripped — filter pills and pagination
    links both append this so neither one drops the other's state."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _insights_breadcrumb():
    return {"label": "Insights", "url": None}


# --------------------------------------------------------------------- Blog

def blog_list(request):
    qs = (
        BlogPost.objects.live()
        .select_related("author")
        .prefetch_related("industries", "tags")
    )
    industry_slug = request.GET.get("industry", "")
    tag_slug = request.GET.get("tag", "")
    if industry_slug:
        qs = qs.filter(industries__slug=industry_slug)
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    context = {
        "page_obj": _paginate(request, qs.distinct()),
        "querystring": _filters_querystring(request),
        "industries": Industry.objects.filter(show_in_nav=True),
        "tags": Tag.objects.all(),
        "active_industry": industry_slug,
        "active_tag": tag_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Blog", "url": None},
        ],
    }
    template = "insights/_blog_results.html" if _is_htmx(request) else "insights/blog_list.html"
    return render(request, template, context)


def blog_post_detail(request, slug):
    manager = BlogPost.objects if _is_preview(request) else BlogPost.objects.live()
    post = get_object_or_404(
        manager.select_related("author").prefetch_related("tags", "industries"), slug=slug,
    )
    reading_minutes = post.reading_minutes or max(1, len(strip_tags(post.body).split()) // 200)
    related_posts = (
        BlogPost.objects.live()
        .filter(Q(tags__in=post.tags.all()) | Q(industries__in=post.industries.all()))
        .exclude(pk=post.pk)
        .distinct()[:3]
    )
    context = {
        "object": post,
        "seo": post,
        "reading_minutes": reading_minutes,
        "related_posts": related_posts,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Blog", "url": reverse("blog_list")},
            {"label": post.title, "url": None},
        ],
    }
    return render(request, "insights/blog_post_detail.html", context)


# -------------------------------------------------------------- Case studies

def case_study_list(request):
    qs = (
        CaseStudy.objects.live()
        .select_related("industry")
        .prefetch_related("services", "metrics")
    )
    industry_slug = request.GET.get("industry", "")
    service_slug = request.GET.get("service", "")
    if industry_slug:
        qs = qs.filter(industry__slug=industry_slug)
    if service_slug:
        qs = qs.filter(services__slug=service_slug)

    context = {
        "page_obj": _paginate(request, qs.distinct()),
        "querystring": _filters_querystring(request),
        "industries": Industry.objects.filter(show_in_nav=True),
        "active_industry": industry_slug,
        "active_service": service_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Case studies", "url": None},
        ],
    }
    template = (
        "insights/_case_study_results.html" if _is_htmx(request) else "insights/case_study_list.html"
    )
    return render(request, template, context)


def case_study_detail(request, slug):
    manager = CaseStudy.objects if _is_preview(request) else CaseStudy.objects.live()
    case_study = get_object_or_404(
        manager.select_related("industry").prefetch_related(
            "services", "metrics", "tech_stack", "testimonials",
        ),
        slug=slug,
    )
    related_use_cases = (
        UseCase.objects.live()
        .filter(industry_id=case_study.industry_id)
        .order_by("order")[:3]
        if case_study.industry_id else UseCase.objects.none()
    )
    context = {
        "object": case_study,
        "seo": case_study,
        # Reuses the services prefetch above rather than a second query —
        # only a tagged service that's actually live is a valid link target.
        "related_services": [s for s in case_study.services.all() if s.is_live],
        "related_use_cases": related_use_cases,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Case studies", "url": reverse("case_study_list")},
            {"label": case_study.title, "url": None},
        ],
    }
    return render(request, "insights/case_study_detail.html", context)


# ----------------------------------------------------------------- Handbooks

def handbook_list(request):
    qs = Handbook.objects.live().prefetch_related("tags")
    tag_slug = request.GET.get("tag", "")
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    context = {
        "page_obj": _paginate(request, qs.distinct()),
        "querystring": _filters_querystring(request),
        "tags": Tag.objects.all(),
        "active_tag": tag_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Handbooks", "url": None},
        ],
    }
    template = "insights/_handbook_results.html" if _is_htmx(request) else "insights/handbook_list.html"
    return render(request, template, context)


def handbook_detail(request, slug):
    manager = Handbook.objects if _is_preview(request) else Handbook.objects.live()
    handbook = get_object_or_404(manager.prefetch_related("tags"), slug=slug)
    context = {
        "object": handbook,
        "seo": handbook,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Handbooks", "url": reverse("handbook_list")},
            {"label": handbook.title, "url": None},
        ],
    }
    if handbook.gated:
        from marketing.forms import HandbookGateForm

        context["form"] = HandbookGateForm(handbook=handbook, initial=utm_initial(request))
    return render(request, "insights/handbook_detail.html", context)


def _make_handbook_download_token(handbook):
    return signing.dumps({"pk": handbook.pk}, salt=HANDBOOK_SALT)


@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def handbook_gate_submit(request, slug):
    """Gated handbook download: save the lead, then hand back a
    time-limited signed download link — never the raw storage path."""
    from marketing.forms import HandbookGateForm  # local import avoids an insights<->marketing cycle

    handbook = get_object_or_404(Handbook.objects.live(), slug=slug, gated=True)
    was_limited = getattr(request, "limited", False)
    if request.method == "POST" and not was_limited:
        form = HandbookGateForm(request.POST, handbook=handbook)
        if form.is_valid():
            submission = form.save()
            notify_staff_of_submission(submission, site_settings=SiteSettings.load())
            token = _make_handbook_download_token(handbook)
            return render(
                request, "insights/_handbook_gate_success.html",
                {"handbook": handbook, "download_url": reverse("handbook_download", args=[token])},
            )
    else:
        form = HandbookGateForm(handbook=handbook, initial=utm_initial(request))
    return render(
        request, "insights/_handbook_gate_form.html",
        {"form": form, "handbook": handbook, "rate_limited": was_limited},
    )


def handbook_download(request, token):
    try:
        data = signing.loads(token, salt=HANDBOOK_SALT, max_age=HANDBOOK_DOWNLOAD_MAX_AGE)
    except signing.BadSignature as exc:
        raise Http404 from exc
    handbook = get_object_or_404(Handbook.objects.live(), pk=data["pk"])
    if not handbook.pdf:
        raise Http404
    filename = handbook.pdf.name.rsplit("/", 1)[-1]
    return FileResponse(handbook.pdf.open("rb"), as_attachment=True, filename=filename)


# ------------------------------------------------------------------ Webinars

def webinar_list(request):
    qs = Webinar.objects.live().prefetch_related("presenters", "tags")
    tag_slug = request.GET.get("tag", "")
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)
    qs = qs.distinct()

    context = {
        "page_obj": _paginate(request, qs),
        "querystring": _filters_querystring(request),
        "tags": Tag.objects.all(),
        "active_tag": tag_slug,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Webinars", "url": None},
        ],
    }
    template = "insights/_webinar_results.html" if _is_htmx(request) else "insights/webinar_list.html"
    return render(request, template, context)


def webinar_detail(request, slug):
    manager = Webinar.objects if _is_preview(request) else Webinar.objects.live()
    webinar = get_object_or_404(manager.prefetch_related("presenters", "tags"), slug=slug)
    context = {
        "object": webinar,
        "seo": webinar,
        "breadcrumbs": [
            {"label": "Home", "url": reverse("home")},
            {"label": "Webinars", "url": reverse("webinar_list")},
            {"label": webinar.title, "url": None},
        ],
    }
    return render(request, "insights/webinar_detail.html", context)
