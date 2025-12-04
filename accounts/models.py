from django.contrib.auth.models import AbstractUser
from django.db import models

from products.models import FinProduct


# Create your models here.


class User(AbstractUser):
    # 아래 속성들은 각 항목에 맞는 값을 선택하기 위한 속성을 정의합니다.
    # 튜플의 첫번째 요소는 DB에 저장되는 값이고, 두번째 요소는 화면에서 보여지는 텍스트입니다.
    GENDER_CHOICES = [
        (True, "남성"),
        (False, "여성"),
    ]

    JOB_CHOICES = [
        ("학생", "학생"),
        ("직장인", "직장인"),
        ("프리랜서", "프리랜서"),
        ("무직", "무직"),
        ("주부", "주부"),
        ("개인사업자", "개인사업자"),
        ("공무원", "공무원"),
        ("군인", "군인"),
        ("기타", "기타"),
    ]

    EARNINGS_CHOICES = [
        ("0원 ~ 1,000만원 미만", "0원 ~ 1,000만원 미만"),
        ("1,000만원 ~ 3,000만원 미만", "1,000만원 ~ 3,000만원 미만"),
        ("3,000만원 ~ 5,000만원 미만", "3,000만원 ~ 5,000만원 미만"),
        ("5,000만원 ~ 1억원 미만", "5,000만원 ~ 1억원 미만"),
        ("1억원 이상", "1억원 이상"),
    ]

    LIFE_AREA_CHOICES = [
        ("서울특별시", "서울특별시"),
        ("부산광역시", "부산광역시"),
        ("인천광역시", "인천광역시"),
        ("대구광역시", "대구광역시"),
        ("대전광역시", "대전광역시"),
        ("광주광역시", "광주광역시"),
        ("울산광역시", "울산광역시"),
        ("세종특별자치시", "세종특별자치시"),
        ("경기도", "경기도"),
        ("충청북도", "충청북도"),
        ("충청남도", "충청남도"),
        ("전라남도", "전라남도"),
        ("경상북도", "경상북도"),
        ("경상남도", "경상남도"),
        ("강원도", "강원도"),
        ("전북특별자치도", "전북특별자치도"),
        ("제주도", "제주도"),
    ]
    # null=True는 DB에 빈 값이 저장되어도 된다는 뜻으로
    # null=True 를 해놓으면 migrate 시 필드가 null값으로 인한
    # 기본 값 설정이나 오류가 발생하지 않습니다.
    # 차후 필드 수정사항이 있다면 동일하게 진행해주세요.
    # verbose_name의 인자로 넣는 문자열이 해당 필드의 이름으로 출력됩니다.
    name = models.CharField(max_length=20, null=True, verbose_name="이름")
    gender = models.BooleanField(null=True, choices=GENDER_CHOICES, verbose_name="성별")
    age = models.IntegerField(null=True, verbose_name="나이")
    job = models.CharField(max_length=30, null=True, choices=JOB_CHOICES, verbose_name="직업")
    earnings = models.CharField(max_length=20, null=True, choices=EARNINGS_CHOICES, verbose_name="소득")
    life_area = models.CharField(max_length=20, null=True, choices=LIFE_AREA_CHOICES, verbose_name="거주지역")
    # 북마크 기능을 위해 상품 정보 테이블과 연결합니다.
    products = models.ManyToManyField(FinProduct, related_name="users")

    @property
    def display_name(self):
        return self.name if self.name else self.username
