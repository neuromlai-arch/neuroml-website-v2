from django.urls import path

from insights import views

urlpatterns = [
    path("blog/", views.blog_list, name="blog_list"),
    path("blog/<slug:slug>/", views.blog_post_detail, name="blog_detail"),
    path("case-studies/", views.case_study_list, name="case_study_list"),
    path("case-studies/<slug:slug>/", views.case_study_detail, name="case_study_detail"),
    path("handbooks/", views.handbook_list, name="handbook_list"),
    path("handbooks/<slug:slug>/", views.handbook_detail, name="handbook_detail"),
    path(
        "handbooks/<slug:slug>/download/",
        views.handbook_gate_submit,
        name="handbook_gate_submit",
    ),
    path(
        "handbooks/download/<str:token>/",
        views.handbook_download,
        name="handbook_download",
    ),
    path("webinars/", views.webinar_list, name="webinar_list"),
    path("webinars/<slug:slug>/", views.webinar_detail, name="webinar_detail"),
]
