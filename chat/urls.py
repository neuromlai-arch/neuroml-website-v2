from django.urls import path

from chat import views

urlpatterns = [
    path("forms/chat/message/", views.chat_message, name="chat_message"),
]
