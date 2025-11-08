"""
chatbot/views.py
폼 전송 방식으로 대화 메시지를 주고받는 간단한 챗봇
AJAX(JSON) 대신 Django의 기본 POST 방식 사용
"""

from django.shortcuts import redirect, render

from .models import ChatMessage


def chat_page(request):
    """
    대화 페이지 렌더링
    - GET 요청: 기존 대화 내역 표시
    - POST 요청: 사용자 입력을 DB에 저장하고 챗봇 응답 생성 후 다시 렌더링
    """
    # POST 요청일 경우 (사용자가 메시지 입력)
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:  # 빈 메시지가 아닐 때만 저장
            # 사용자 메시지 저장
            ChatMessage.objects.create(role="user", message=user_message)

            # 규칙 기반 응답 로직
            if "예금" in user_message:
                reply = "현재 제공 중인 정기예금 금리는 평균 3.2%입니다."
            elif "환율" in user_message:
                reply = "오늘의 환율은 달러당 1,321원입니다."
            elif "보험" in user_message:
                reply = "현재 추천 보험 상품은 실손의료보험과 운전자보험입니다."
            else:
                reply = "죄송해요, 아직 그 질문은 학습되지 않았어요."

            # 챗봇 응답 저장
            ChatMessage.objects.create(role="bot", message=reply)

        # POST 후 새로고침 시 중복 전송 방지를 위해 리다이렉트
        return redirect("chat:chat_page")

    # GET 요청일 경우 (화면 처음 열었을 때 or 새로고침)
    messages = ChatMessage.objects.all().order_by("created_at")  # 오래된 순
    return render(request, "chatbot/chat.html", {"messages": messages})
