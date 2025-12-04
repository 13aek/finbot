from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm


# 초기에 설정해놓은 커스텀 유저 모델로 갱신
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()

    def save(self, commit=True):
        user = super().save(commit=False)

        # name 입력칸 없으므로 username으로 자동 설정
        user.name = user.username

        if commit:
            user.save()
        return user


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
