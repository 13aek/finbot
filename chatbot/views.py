"""
chatbot/views.py
폼 전송 방식으로 대화 메시지를 주고받는 간단한 챗봇
AJAX(JSON) 대신 Django의 기본 POST 방식 사용
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from products.models import FinProduct
from rag_flow.graph_flow import ChatSession

from .forms import ChatRoomForm
from .models import ChatMessage, ChatRoom


@login_required
def chatroom_create(request):
    """
    POST 요청: 사용자의 요청을 받아 새로운 채팅방을 생성합니다.
    """

    last_room = ChatRoom.objects.filter(user=request.user).order_by("-display_id").first()
    if last_room:
        next_id = last_room.display_id + 1
    else:
        next_id = 1

    chatroom = ChatRoom.objects.create(user=request.user, display_id=next_id)
    # 생성한 채팅방으로 리다이렉트
    return redirect("chat:chat_page", chatroom.pk)


def chatroom_delete(requset, chatroom_pk):
    """
    POST 요청: 사용자의 요청을 받아 해당 채팅방을 삭제합니다.
    """
    # 삭제할 채팅방 조회
    chatroom = ChatRoom.objects.get(pk=chatroom_pk)
    # 조회한 채팅방이 해당 유저의 채팅방인지 확인합니다.
    if chatroom.user == requset.user:
        chatroom.delete()
        # 가장 최근의 채팅방으로 리다이렉트
        return redirect("chat:current_chat")


@login_required
def chat_page(request, chatroom_pk=None):
    """
    대화 페이지 렌더링
    - GET 요청: 기존 대화 내역 표시
    - POST 요청: 사용자 입력을 DB에 저장하고 챗봇 응답 생성 후 다시 렌더링
    """
    # 채팅방이 하나도 없다면 채팅방을 하나 자동으로 생성합니다.
    rooms = ChatRoom.objects.filter(user=request.user)
    if not rooms.exists():
        return chatroom_create(request)

    # 유저가 메인페이지에서 채팅방 페이지를 요청한 경우
    if not chatroom_pk:
        # 가장 최근의 대화를 나눴던 대화를 조회합니다.
        current_chat = ChatMessage.objects.filter(user=request.user).order_by("-created_at").first()
        # 만약 나눴던 대화가 없다면 가장 최근에 생성된 채팅방을 조회합니다.
        if not current_chat:
            chat_room = ChatRoom.objects.filter(user=request.user).order_by("-created_at").first()
        else:
            # 가장 최근에 나눴던 대화를 통해 가장 최근에 대화를 나눴던 채팅방을 조회합니다.
            chat_room = current_chat.room
        # 채팅방의 고유키를 할당합니다.
        chatroom_pk = chat_room.pk

    # 유저가 채팅방을 이동하는 경우
    # 해당 사용자의 채팅방을 조회합니다.
    else:
        chat_room = ChatRoom.objects.get(pk=chatroom_pk)
    # 요청한 채팅방이 사용자의 채팅방이 맞는지 확인합니다.
    if chat_room.user != request.user:
        return redirect("chat:chat_list")

    # 사용자가 이전 로그인 시점에 챗봇과 나눴던 대화를 불러옵니다.
    chat_history = chat_room.history

    # langgraph_flow를 따르기 위해 ChatSession의 인스턴스를 생성합니다.
    # 현재 사용자의 이전 로그인 시점의 대화 히스토리를 인스턴스 변수로 생성합니다.
    chat = ChatSession(chat_history)
    user_thread = {"configurable": {"thread_id": chatroom_pk, "user_id": request.user.pk}}

    # POST 요청일 경우 (사용자가 메시지 입력)
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:  # 빈 메시지가 아닐 때만 저장
            # 사용자 메시지 저장
            ChatMessage.objects.create(user=request.user, room=chat_room, role="user", message=user_message)
            # 세션에 임시로 현재 로그인 상태에서 사용자가 보냈던 메시지를 저장합니다.
            # 이미 세션에 저장된 메시지가 있다면 추가합니다.
            if request.session.get(f"chat{chatroom_pk}"):
                request.session[f"chat{chatroom_pk}"] = request.session.get(f"chat{chatroom_pk}") + ", " + user_message
            else:
                request.session[f"chat{chatroom_pk}"] = user_message

            # langgraph의 flow에 따라 chat 인스턴스에 히스토리를 "new"로 추가합니다.
            chat.state["history"].append({"role": "user", "content": user_message, "state": "new"})

            # 챗봇 응답 저장
            if request.session.get("need_user_feedback"):
                reply = chat.ask(user_message, user_thread, request.session["need_user_feedback"])
                request.session["need_user_feedback"] = False
            else:
                reply = chat.ask(user_message, user_thread)
            print(reply)
            if reply["need_user_feedback"]:
                answer = [reply["answer"], reply["__interrupt__"][0].value]
            else:
                answer = reply["answer"]
            request.session["need_user_feedback"] = reply["need_user_feedback"]
            ChatMessage.objects.create(user=request.user, room=chat_room, role="bot", message=answer)

            # 챗봇의 응답을 바탕으로 추천받은 금융 상품이 있다면 해당 상품을 외래키로 가지는 채팅을 하나 추가합니다.
            if chat.state.get("product_code"):
                # 추천받은 상품
                product = FinProduct.objects.get(fin_prdt_cd=chat.state["product_code"])
                ChatMessage.objects.create(
                    user=request.user, room=chat_room, role="bot", message="추천상품", product=product
                )

        # POST 후 새로고침 시 중복 전송 방지를 위해 리다이렉트
        return redirect("chat:chat_page", chatroom_pk)

    # GET 요청일 경우 (화면 처음 열었을 때 or 새로고침)
    # 첫 방문인 경우에는 방문처리 후 인삿말을 출력합니다.
    if not chat_room.ever_visited:
        chat_room.ever_visited = True
        chat_room.save()
        # langgraph flow에 따라 질문이 없다면 인삿말을 출력합니다.
        reply = chat.ask(None, user_thread)
        answer = reply["answer"]
        # 중복 인사를 방지하기 위해 세션에 로그인 상태를 기록합니다.
        request.session[f"login_visited{chatroom_pk}"] = True
        ChatMessage.objects.create(user=request.user, room=chat_room, role="bot", message=answer)

    # 2번째 방문 이상이고 그 로그인의 첫 방문인 경우 인삿말을 출력합니다.
    if not request.session.get(f"login_visited{chatroom_pk}") and chat_history:
        reply = chat.ask(None, user_thread)
        answer = reply["answer"]
        # 중복 인사를 방지하기 위해 세션에 로그인 상태를 기록합니다.
        request.session[f"login_visited{chatroom_pk}"] = True
        ChatMessage.objects.create(user=request.user, room=chat_room, role="bot", message=answer)
    # 사용자의 모든 채팅방을 조회
    rooms = ChatRoom.objects.filter(user=request.user)
    # 현재 채팅방의 메시지만 조회
    messages = ChatMessage.objects.filter(room=chat_room).order_by("created_at")  # 오래된 순
    context = {
        "messages": messages,
        "rooms": rooms,
        "chatroom_pk": chatroom_pk,  # 사용자가 어떤 채팅방에 머무르는지 확인할 수 있도록 현재 채팅방의 pk를 넘겨줍니다.
    }
    return render(request, "chatbot/chat.html", context)


def chatroom_update(request, chatroom_pk):
    """
    # 사용자의 요청을 받아 채팅방의 이름을 변경합니다.
    GET: 채팅방 변경 페이지 랜더링
    POST: 채팅방 이름의 변경 사항을 DB에 저장
    """
    # 수정할 채팅방을 조회
    room = ChatRoom.objects.get(pk=chatroom_pk)
    # 채팅방의 사용자와 현재 요청한 사용자가 다르면 메인페이지로 리다이렉트 시킴
    if room.user != request.user:
        return redirect("products:index")
    # 사용자의 요청 메서드에 따라 분기
    if request.method == "POST":
        form = ChatRoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            return redirect("chat:chat_page", room.pk)
        # GET 요청인 경우 채팅방 이름 변경 페이지를 랜더링
    else:
        form = ChatRoomForm(instance=room)
    context = {
        "form": form,
        "room": room,
    }
    return render(request, "chatbot/update.html", context)
