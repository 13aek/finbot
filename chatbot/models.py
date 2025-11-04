from django.db import models


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("bot", "Bot"),
    ]

    # ✅ 역할 (유저/봇)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # ✅ 메시지 내용
    message = models.TextField()

    # ✅ 생성 시각
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"  # MySQL 테이블명
        ordering = ["created_at"]  # 최신순 정렬

    def __str__(self):
        return f"[{self.role}] {self.message[:30]}"
