from django.urls import path

from careers import views
from careers.models import JobPosting
from core.views import stub_detail

urlpatterns = [
    path(
        "careers/<slug:slug>/", stub_detail, {"model": JobPosting}, name="job_posting_detail",
    ),
    path(
        "careers/applications/<str:token>/download/",
        views.resume_download,
        name="resume_download",
    ),
]
