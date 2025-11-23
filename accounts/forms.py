from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm


# ================================================================
# CustomUserCreationForm
# - 기존 UserCreationForm을 기반으로 커스텀 유저 모델(get_user_model) 사용
# - Django 기본 에러 메시지가 영어로 출력되는 문제를 해결하기 위해
#   필드별 error_messages를 한국어로 재정의
# - 필수 변경 최소화 (협업 시 충돌 방지)
# ================================================================
class CustomUserCreationForm(UserCreationForm):

    # username 필드 오류 메시지 재정의 (아이디 관련)
    username = forms.CharField(
        label="아이디",
        error_messages={
            "required": "아이디를 입력해주세요.",
            "unique": "이미 사용 중인 아이디입니다.",
        }
    )

    # 비밀번호 입력 필드
    password1 = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput,
        error_messages={
            "required": "비밀번호를 입력해주세요.",
        }
    )

    # 비밀번호 재입력 필드
    password2 = forms.CharField(
        label="비밀번호 확인",
        widget=forms.PasswordInput,
        error_messages={
            "required": "비밀번호를 다시 입력해주세요.",
        }
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

    # 비밀번호 불일치 메시지
    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("비밀번호가 서로 일치하지 않습니다.")
        return p2

# CustomUserChangeForm
# - 마이페이지 등에서 사용자 정보 수정 시 사용하는 Form
# 초기에 설정해놓은 커스텀 유저 모델로 갱신

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        # Todo: 출력 필드 상의 후 재정의 필요
        # ex)
        # fields = ('first_name', 'last_name')
        fields = [
            "name",
            "age",
            "job",
            "gender",
            "earnings",
            "life_area",
        ]
