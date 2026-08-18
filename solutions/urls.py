from django.urls import path

from core.views import stub_detail
from solutions.models import HireRole, Product, Service, Technology, UseCase

urlpatterns = [
    path(
        "services/<slug:slug>/", stub_detail, {"model": Service}, name="service_detail",
    ),
    path(
        "use-cases/<slug:slug>/", stub_detail, {"model": UseCase}, name="use_case_detail",
    ),
    path(
        "products/<slug:slug>/", stub_detail, {"model": Product}, name="product_detail",
    ),
    path(
        "technologies/<slug:slug>/",
        stub_detail,
        {"model": Technology},
        name="technology_detail",
    ),
    path(
        "hire/<slug:slug>/", stub_detail, {"model": HireRole}, name="hire_role_detail",
    ),
]
