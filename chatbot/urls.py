from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("<int:chatroom_pk>/", views.chat_page, name="chat_page"),  # 대화 페이지
    path("chatlist/", views.chat_list, name="chat_list"), # 모든 채팅방 조회 페이지
    path("chatroom/create/", views.chatroom_create, name="chatroom_create"),
]
