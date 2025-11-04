import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import ChatMessage


# ✅ HTML 페이지 렌더링 (대화창)
def chat_page(request):
    """
    간단한 채팅 페이지 렌더링
    templates/chatbot/chat.html 을 렌더링함
    """
    messages = ChatMessage.objects.all().order_by("-created_at")[:20]  # 최근 20개 대화
    return render(request, "chatbot/chat.html", {"messages": messages})


@csrf_exempt
def ask_chatbot(request):
    """
    간단한 챗봇 API 엔드포인트
    - POST 요청으로 message를 받음
    - DB(ChatMessage)에 사용자 및 봇 메시지를 저장
    - 기본 규칙 기반 응답 반환
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST 요청만 지원합니다."}, status=400)

    try:
        # JSON 파싱
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 요청입니다."}, status=400)

    # 메시지 추출
    user_message = data.get("message", "").strip()
    if not user_message:
        return JsonResponse({"error": "메시지가 비어 있습니다."}, status=400)

    # 1️⃣ 사용자 메시지 저장
    ChatMessage.objects.create(role="user", message=user_message)

    # 2️⃣ 간단한 규칙 기반 응답 로직
    if "예금" in user_message:
        reply = "현재 제공 중인 정기예금 금리는 평균 3.2%입니다."
    elif "환율" in user_message:
        reply = "오늘의 환율은 달러당 1,321원입니다."
    elif "보험" in user_message:
        reply = "현재 추천 보험 상품은 실손의료보험과 운전자보험입니다."
    else:
        reply = "죄송해요, 아직 그 질문은 학습되지 않았어요."

    # 3️⃣ 봇 응답 저장
    ChatMessage.objects.create(role="bot", message=reply)

    # 4️⃣ JSON 응답 반환 (ensure_ascii=False로 한글 깨짐 방지)
    return JsonResponse({"reply": reply}, json_dumps_params={"ensure_ascii": False})
