from django.conf import settings
from django.db import models

from products.models import FinProduct


class ChatRoom(models.Model):
    # 외래키와 같은 방식으로 User모델과 관계를 맺지만, 각 객체가 오직 하나의 연결만 가지도록 설정
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # 사용자가 방문한 적 있는지 없는지를 표시할 필드
    ever_visited = models.BooleanField(default=False)

    # 사용자가 이전 로그인 세션에서 나눴던 대화
    history = models.TextField(null=True)

    # 사용자에게 보여줄 방 번호
    display_id = models.PositiveIntegerField()  # 음수가 없는 필드

    # 채팅방 이름
    title = models.CharField(max_length=15, null=True)


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("bot", "Bot"),
    ]
    # 유저와 연결
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # 채팅방과 연결
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)

    # 역할 (유저/봇)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # 메시지 내용
    message = models.TextField()

    # 생성 시각
    created_at = models.DateTimeField(auto_now_add=True)

    # 상품 추천 메시지라면 FK로 저장
    product = models.ForeignKey(
        FinProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommended_messages"
    )

    class Meta:
        ordering = ["created_at"]  # 최신순 정렬

    def __str__(self):
        return f"[{self.role}] {self.message[:30]}"
