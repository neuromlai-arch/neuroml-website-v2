from django.urls import path

from core.views import stub_detail
from solutions.models import Product, Service, UseCase

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
]
