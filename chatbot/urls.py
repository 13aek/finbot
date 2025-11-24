from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_page, name="currnet_chat"), # 가장 최근의 채팅 페이지
    path("<int:chatroom_pk>/", views.chat_page, name="chat_page"),  # 대화 페이지
    path("chatlist/", views.chat_list, name="chat_list"), # 모든 채팅방 조회 페이지
    path("chatroom/create/", views.chatroom_create, name="chatroom_create"), # 채팅방 생성
    path("chatroom/delete/<int:chatroom_pk>/", views.chatroom_delete, name="chatroom_delete"), # 채팅방 삭제
    path("chatroom/update/<int:chatroom_pk>/", views.chatroom_update, name="chatroom_update"), # 채팅방 이름 변경
    
]
