from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


# 초기에 설정해놓은 커스텀 유저 모델로 갱신
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
