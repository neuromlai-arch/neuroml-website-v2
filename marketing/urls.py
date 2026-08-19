from django.urls import path

from marketing import views

urlpatterns = [
    path("book-a-demo/", views.demo, name="demo"),
    path("forms/contact/", views.contact_submit, name="contact_submit"),
    path("forms/demo/", views.demo_submit, name="demo_submit"),
    path("forms/popup/", views.popup_submit, name="popup_submit"),
    path("forms/newsletter/", views.newsletter_signup, name="newsletter_signup"),
    path("newsletter/confirm/<str:token>/", views.newsletter_confirm, name="newsletter_confirm"),
]
