from django.urls import path

from core.views import stub_detail
from taxonomy.models import Industry

urlpatterns = [
    path(
        "industries/<slug:slug>/",
        stub_detail,
        {"model": Industry},
        name="industry_detail",
    ),
]
