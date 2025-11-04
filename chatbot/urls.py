from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_page, name="chat_page"),  # 대화 페이지
]
