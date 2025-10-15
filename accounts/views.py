from django.shortcuts import redirect, render

from .forms import CustomUserCreationForm

# Create your views here.


def test(request):
    return render(request, "accounts/test.html")


def signup(request):
    """
    사용자의 http 메서드 요청에 따라 회원가입 페이지를 응답하거나
    사용자가 입력한 정보를 DB에 저장하는 함수
    """

    # 사용자가 정보를 입력하고 회원가입을 요청했을 때
    if request.method == "POST":
        # 사용자가 보낸 요청을 변수에 할당
        form = CustomUserCreationForm(request.POST)
        # 유효성 검사 진행
        if form.is_valid():
            form.save()
            # 메인 페이지 생성 후 메인페이지로 리다이렉트 되도록 수정 필요
            return redirect("accounts:test")

    # 사용자가 회원가입 페이지를 요청했을 때
    else:
        form = CustomUserCreationForm()

    context = {
        "form": form,
    }
    return render(request, "accounts/signup.html", context)
