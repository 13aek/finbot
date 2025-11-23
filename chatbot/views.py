"""
chatbot/views.py
폼 전송 방식으로 대화 메시지를 주고받는 간단한 챗봇
AJAX(JSON) 대신 Django의 기본 POST 방식 사용
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from rag_flow.graph_flow import ChatSession

from .models import ChatMessage, ChatRoom


@login_required
def chat_page(request):
    """
    대화 페이지 렌더링
    - GET 요청: 기존 대화 내역 표시
    - POST 요청: 사용자 입력을 DB에 저장하고 챗봇 응답 생성 후 다시 렌더링
    """
    # 로그인 여부 체크 — 메시지 + 로그인 페이지로 redirect
    if not request.user.is_authenticated:
        messages.warning(request, "회원만 이용 가능합니다. 로그인 후 이용해주세요.")
        return redirect("accounts:login")
    
    
    # 해당 사용자의 채팅방을 조회합니다.
    chat_room = ChatRoom.objects.get(user=request.user)
    # 사용자가 이전 로그인 시점에 챗봇과 나눴던 대화를 불러옵니다.
    chat_history = chat_room.history

    # langgraph_flow를 따르기 위해 ChatSession의 인스턴스를 생성합니다.
    # 현재 사용자의 이전 로그인 시점의 대화 히스토리를 인스턴스 변수로 생성합니다.
    chat = ChatSession(chat_history)

    # POST 요청일 경우 (사용자가 메시지 입력)
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:  # 빈 메시지가 아닐 때만 저장
            # 사용자 메시지 저장
            ChatMessage.objects.create(
                user=request.user, role="user", message=user_message
            )
            # 세션에 임시로 현재 로그인 상태에서 사용자가 보냈던 메시지를 저장합니다.
            # 이미 세션에 저장된 메시지가 있다면 추가합니다.
            if request.session.get("chat"):
                request.session["chat"] = (
                    request.session.get("chat") + ", " + user_message
                )
            else:
                request.session["chat"] = user_message

            # langgraph의 flow에 따라 chat 인스턴스에 히스토리를 "new"로 추가합니다.
            chat.state["history"].append(
                {"role": "user", "content": user_message, "state": "new"}
            )

            # 챗봇 응답 저장
            reply = chat.ask(user_message)
            ChatMessage.objects.create(user=request.user, role="bot", message=reply)

        # POST 후 새로고침 시 중복 전송 방지를 위해 리다이렉트
        return redirect("chat:chat_page")

    # GET 요청일 경우 (화면 처음 열었을 때 or 새로고침)
    # 첫 방문인 경우에는 방문처리 후 인삿말을 출력합니다.
    if not chat_room.ever_visited:
        chat_room.ever_visited = True
        chat_room.save()
        # langgraph flow에 따라 질문이 없다면 인삿말을 출력합니다.
        reply = chat.ask(None)
        # 중복 인사를 방지하기 위해 세션에 로그인 상태를 기록합니다.
        request.session["login_visited"] = True
        ChatMessage.objects.create(user=request.user, role="bot", message=reply)

    # 2번째 방문 이상이고 그 로그인의 첫 방문인 경우 인삿말을 출력합니다.
    if not request.session.get("login_visited") and chat_history:
        reply = chat.ask(None)
        # 중복 인사를 방지하기 위해 세션에 로그인 상태를 기록합니다.
        request.session["login_visited"] = True
        ChatMessage.objects.create(user=request.user, role="bot", message=reply)

    # 현재 사용자의 메시지만 조회
    messages = ChatMessage.objects.filter(user=request.user).order_by(
        "created_at"
    )  # 오래된 순
    return render(request, "chatbot/chat.html", {"messages": messages})
