from django.urls import path

from core.views import stub_detail
from insights.models import BlogPost, CaseStudy, Handbook, Webinar

urlpatterns = [
    path("blog/<slug:slug>/", stub_detail, {"model": BlogPost}, name="blog_detail"),
    path(
        "case-studies/<slug:slug>/",
        stub_detail,
        {"model": CaseStudy},
        name="case_study_detail",
    ),
    path(
        "handbooks/<slug:slug>/", stub_detail, {"model": Handbook}, name="handbook_detail",
    ),
    path("webinars/<slug:slug>/", stub_detail, {"model": Webinar}, name="webinar_detail"),
]
