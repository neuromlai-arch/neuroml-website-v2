from django.urls import path

from solutions import views

urlpatterns = [
    path("services/", views.service_list, name="service_list"),
    path("services/<slug:slug>/", views.service_detail, name="service_detail"),
    path("use-cases/", views.use_case_list, name="use_case_list"),
    path("use-cases/<slug:slug>/", views.use_case_detail, name="use_case_detail"),
    path("products/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("technologies/", views.technology_list, name="technology_list"),
    path("technologies/<slug:slug>/", views.technology_detail, name="technology_detail"),
    path("hire/", views.hire_role_list, name="hire_role_list"),
    path("hire/<slug:slug>/", views.hire_role_detail, name="hire_role_detail"),
]
