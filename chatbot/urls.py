from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_page, name="chat_page"),  # ✅ HTML 렌더링
    path("ask/", views.ask_chatbot, name="ask_chatbot"),  # ✅ AJAX 요청 처리
]
