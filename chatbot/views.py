"""
chatbot/views.py
폼 전송 방식으로 대화 메시지를 주고받는 간단한 챗봇
AJAX(JSON) 대신 Django의 기본 POST 방식 사용
"""

from django.shortcuts import redirect, render

from rag_flow.graph_flow import ChatSession

from .models import ChatMessage, ChatRoom


def chat_page(request):
    """
    대화 페이지 렌더링
    - GET 요청: 기존 대화 내역 표시
    - POST 요청: 사용자 입력을 DB에 저장하고 챗봇 응답 생성 후 다시 렌더링
    """
    # 사용자의 채팅방 조회
    chat_room = ChatRoom.objects.get(user=request.user)
    # 사용자의 채팅 히스토리 조회
    chat_history = chat_room.history

    # 채팅 인스턴스 생성
    chat = ChatSession(request.user.pk, chat_history)

    # POST 요청일 경우 (사용자가 메시지 입력)
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:  # 빈 메시지가 아닐 때만 저장
            # 사용자 메시지 저장
            ChatMessage.objects.create(
                room=chat_room, role="user", message=user_message
            )
            # 세션에 임시로 현재 로그인 상태에서 사용자가 보냈던 메시지를 저장
            if request.session.get("chat"):
                request.session["chat"] = (
                    request.session.get("chat") + ", " + user_message
                )
            else:
                request.session["chat"] = user_message
            # 채팅 인스턴스 히스토리에 사용자 메시지 저장
            chat.state["history"].append(
                {"role": "user", "content": user_message, "state": "new"}
            )

            reply = chat.ask(user_message)
            # 챗봇 응답 저장
            ChatMessage.objects.create(room=chat_room, role="bot", message=reply)

        # POST 후 새로고침 시 중복 전송 방지를 위해 리다이렉트
        return redirect("chat:chat_page")

    # GET 요청일 경우 (화면 처음 열었을 때 or 새로고침)
    # 첫 방문인 경우에는 방문처리 후 인삿말을 출력
    if not chat_room.ever_visited:
        chat_room.ever_visited = True
        chat_room.save()
        reply = chat.ask(None)
        ChatMessage.objects.create(room=chat_room, role="bot", message=reply)

    # 2번째 방문 이상이고 그 로그인의 첫 방문인 경우 인삿말 출력
    if not request.session.get("login_visited"):
        reply = chat.ask(None)
        # 방문처리
        request.session["login_visited"] = True
        ChatMessage.objects.create(room=chat_room, role="bot", message=reply)

    messages = ChatMessage.objects.all().order_by("created_at")  # 오래된 순
    return render(request, "chatbot/chat.html", {"messages": messages})
