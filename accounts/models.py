from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    # null=True는 DB에 빈 값이 저장되어도 된다는 뜻으로
    # null=True 를 해놓으면 migrate 시 필드가 null값으로 인한
    # 기본 값 설정이나 오류가 발생하지 않습니다.
    # 차후 필드 수정사항이 있다면 동일하게 진행해주세요.
    name = models.CharField(max_length=20, null=True)
    gender = models.BooleanField(null=True)
    age = models.IntegerField(null=True)
    job = models.CharField(null=True)
    earnings = models.CharField(max_length=20, null=True)
    life_area = models.CharField(max_length=20, null=True)
