from django.urls import path

from pages import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "partials/home-industry/<slug:slug>/",
        views.home_industry_panel,
        name="home_industry_panel",
    ),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("preview/<str:token>/", views.preview, name="content_preview"),
]
