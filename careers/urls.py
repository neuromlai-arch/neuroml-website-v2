from django.urls import path

from careers import views

urlpatterns = [
    path("careers/", views.job_posting_list, name="job_posting_list"),
    path(
        "careers/applications/<str:token>/download/",
        views.resume_download,
        name="resume_download",
    ),
    path(
        "careers/<slug:slug>/", views.job_posting_detail, name="job_posting_detail",
    ),
    path(
        "careers/<slug:slug>/apply/",
        views.job_application_submit,
        name="job_application_submit",
    ),
]
