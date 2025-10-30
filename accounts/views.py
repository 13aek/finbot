from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
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
    if request.user.is_authenticated:
        return redirect("accounts:test")

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
    """
    사용자의 http 메서드 요청에 따라 로그인 페이지를 응답하거나
    사용자가 입력한 정보를 검증해 로그인 세션을 생성하는 함수
    """
    if request.user.is_authenticated:
        return redirect("accounts:test")

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


@login_required
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


@login_required
def password(request):
    """
    현재 로그인한 사용자의 비밀번호를 변경하는 함수
    Args:
        request (HttpRequest): 클라이언트의 HTTP 요청 객체

    Returns:
        HttpResponse:
            - GET 요청일 경우, 비밀번호 수정 페이지(`accounts/password.html`)를 렌더링합니다.
            - POST 요청에서 폼이 유효하면, 비밀번호 변경 후 테스트 페이지로 리다이렉트합니다.
    """
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            return redirect("accounts:test")
    else:
        form = PasswordChangeForm(request.user)
    context = {
        "form": form,
    }
    return render(request, "accounts/password.html", context)


@login_required
def logout(request):
    """
    현재 로그인한 사용자를 로그아웃시키는 뷰 함수

    Django의 `logout()` 함수를 호출하여 세션 정보를 삭제하고,
    로그아웃 후 로그인 페이지로 리다이렉트합니다.

    Args:
        request (HttpRequest): 클라이언트의 HTTP 요청 객체

    Returns:
        HttpResponseRedirect: 로그아웃 처리 후 로그인 페이지(`accounts:login`)로 리다이렉트합니다.
    """
    auth_logout(request)
    return redirect("accounts:login")


@login_required
def delete(request):
    """
    회원 탈퇴 기능
    현재 로그인한 사용자를 삭제(회원탈퇴)하는 뷰 함수

    사용자의 요청에 따라 DB에서 해당 User 객체를 삭제하고,
    로그아웃 처리 후 테스트 페이지(`accounts/test.html`)로 리다이렉트

    Args:
        request (HttpRequest): 클라이언트의 HTTP 요청 객체

    Returns:
        HttpResponse:
            - POST 요청일 경우, 현재 로그인한 사용자를 삭제하고 로그아웃 처리 후 테스트 페이지로 리다이렉트
            - GET 요청으로 접근 시, 직접적인 렌더링은 없으며 보통 탈퇴 버튼(Form action)으로 요청

    """
    request.user.delete()
    return redirect("accounts:test")
