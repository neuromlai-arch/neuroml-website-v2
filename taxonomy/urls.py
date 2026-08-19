from django.urls import path

from taxonomy import views

urlpatterns = [
    path("industries/", views.industry_list, name="industry_list"),
    path("industries/<slug:slug>/", views.industry_detail, name="industry_detail"),
]
