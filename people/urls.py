from django.urls import path

from people import views

urlpatterns = [
    path("team/<slug:slug>/", views.team_member_detail, name="team_member_detail"),
]
