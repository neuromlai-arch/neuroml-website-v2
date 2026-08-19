"""Resume downloads never expose the raw storage path — a staff member gets a
signed, time-limited URL instead (mirrors pages.views' preview-token pattern).
"""

from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django_ratelimit.decorators import ratelimit

from careers.forms import JobApplicationForm
from careers.models import JobApplication, JobPosting
from core.notifications import notify_staff_of_application
from core.utm import utm_initial
from pages.models import SiteSettings

RESUME_SALT = "careers.resume"
RESUME_MAX_AGE = 60 * 15  # 15 minutes


def make_resume_token(application):
    return signing.dumps({"pk": application.pk}, salt=RESUME_SALT)


def resume_download(request, token):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise PermissionDenied

    try:
        data = signing.loads(token, salt=RESUME_SALT, max_age=RESUME_MAX_AGE)
    except signing.BadSignature as exc:
        raise Http404 from exc

    application = get_object_or_404(JobApplication, pk=data["pk"])
    filename = application.resume.name.rsplit("/", 1)[-1]
    return FileResponse(
        application.resume.open("rb"), as_attachment=True, filename=filename,
    )


def job_posting_list(request):
    postings = JobPosting.objects.live().order_by("-published_at")

    department = request.GET.get("department", "")
    work_mode = request.GET.get("work_mode", "")
    employment_type = request.GET.get("employment_type", "")
    if department:
        postings = postings.filter(department=department)
    if work_mode:
        postings = postings.filter(work_mode=work_mode)
    if employment_type:
        postings = postings.filter(employment_type=employment_type)

    page_obj = Paginator(postings, 12).get_page(request.GET.get("page"))

    querystring_params = request.GET.copy()
    querystring_params.pop("page", None)
    querystring = querystring_params.urlencode()

    context = {
        "page_obj": page_obj,
        "querystring": querystring,
        "departments": JobPosting.objects.live().values_list(
            "department", flat=True,
        ).exclude(department="").distinct().order_by("department"),
        "work_modes": JobPosting.WorkMode.choices,
        "employment_types": JobPosting.EmploymentType.choices,
        "selected_department": department,
        "selected_work_mode": work_mode,
        "selected_employment_type": employment_type,
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Careers", "url": None},
        ],
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "careers/_job_posting_results.html", context)
    return render(request, "careers/job_posting_list.html", context)


def job_posting_detail(request, slug):
    is_preview = (
        request.GET.get("preview") == "1"
        and request.user.is_authenticated
        and request.user.is_staff
    )
    manager = JobPosting.objects if is_preview else JobPosting.objects.live()
    job = get_object_or_404(manager, slug=slug)

    breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Careers", "url": "/careers/"},
        {"label": job.title, "url": None},
    ]
    context = {"object": job, "seo": job, "job": job, "breadcrumbs": breadcrumbs}
    if job.is_open:
        context["form"] = JobApplicationForm(job=job, initial=utm_initial(request))
    return render(request, "careers/job_posting_detail.html", context)


@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def job_application_submit(request, slug):
    """Resume validation (type/size) already lives on the model field's
    validators — surfaced here as ordinary form errors."""
    job = get_object_or_404(JobPosting.objects.live(), slug=slug, is_open=True)
    was_limited = getattr(request, "limited", False)
    if request.method == "POST" and not was_limited:
        form = JobApplicationForm(request.POST, request.FILES, job=job)
        if form.is_valid():
            application = form.save()
            notify_staff_of_application(application, site_settings=SiteSettings.load())
            return render(request, "components/_form_success.html", {
                "message": "Thanks — we'll be in touch if it's a fit.",
            })
    else:
        form = JobApplicationForm(job=job, initial=utm_initial(request))
    return render(
        request, "careers/_job_application_form.html",
        {"form": form, "job": job, "rate_limited": was_limited},
    )
