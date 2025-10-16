from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .forms import CustomUserChangeForm, CustomUserCreationForm


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


# 로그인 기능 구현
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect("accounts:test")
    else:
        form = AuthenticationForm()
    context = {
        "form": form,
    }
    return render(request, "accounts/login.html", {"form": form})


def update(request):
    """
    현재 로그인한 사용자의 프로필 정보를 수정하는 뷰 함수
    
    Args:
        request (HttpRequest): 클라이언트의 HTTP 요청 객체

    Returns:
        HttpResponse: 
            - GET 요청일 경우, 프로필 수정 페이지(`accounts/update.html`)를 렌더링합니다.
            - POST 요청에서 폼이 유효하면, 프로필 수정 후 해당 페이지로 리다이렉트합니다.
    """
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:update")
    else:
        form = CustomUserChangeForm(instance=request.user)
    context = {
        "form": form,
    }
    return render(request, "accounts/update.html", context)
