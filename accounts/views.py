from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

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
    """
    사용자의 http 메서드 요청에 따라 로그인 페이지를 응답하거나
    사용자가 입력한 정보를 검증해 로그인 세션을 생성하는 함수
    """

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
              만약 비밀번호 재확인이 이루어지지 않았다면 비밀번호 입력 페이지로 리다이렉트합니다.
            - POST 요청에서 폼이 유효하면, 프로필 수정 후 해당 페이지로 리다이렉트합니다.
    """
    # 비밀번호 재확인이 완료되었는지 확인합니다.
    verified_time = request.session.get("password_verified")
    # 현재의 초 단위와, 과거에 세션을 저장했던 초 단위를 비교하여 만료 여부를 결정합니다.
    if not verified_time or (timezone.now().timestamp() - verified_time > 300):
        # 세션이 없거나 만료되었다면 비밀번호를 재확인합니다.
        # 쿼리스트링을 통해 비밀번호 인증 후 다음에 이동할 페이지를 결정합니다.
        return redirect(
            f"{reverse('accounts:verify')}?next={reverse('accounts:update')}"
        )

    # 인증이 완료되었다면 바로 인증이 필요한 서비스 이용 시 한번 더 인증하도록 세션을 삭제합니다.
    request.session.pop("password_verified", None)

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

    만약 비밀번호 인증이 완료되지 않았다면 비밀번호 인증 페이지로 리다이렉트

    사용자의 요청에 따라 DB에서 해당 User 객체를 삭제하고,
    로그아웃 처리 후 테스트 페이지(`accounts/test.html`)로 리다이렉트

    Args:
        request (HttpRequest): 클라이언트의 HTTP 요청 객체

    Returns:
        HttpResponse:
            - POST 요청일 경우, 현재 로그인한 사용자를 삭제하고 로그아웃 처리 후 테스트 페이지로 리다이렉트
            - GET 요청으로 접근 시, 직접적인 렌더링은 없으며 보통 탈퇴 버튼(Form action)으로 요청

    """
    # 비밀번호 재확인 세션이 없거나 만료된 경우
    verified_time = request.session.get("password_verified")
    if not verified_time or (timezone.now().timestamp() - verified_time > 300):
        # 세션이 없거나 만료된경우 비밀번호 인증 페이지로 이동합니다.
        return redirect(
            f"{reverse('accounts:verify')}?next={reverse('accounts:delete')}"
        )
    request.user.delete()
    return redirect("accounts:test")


@login_required
def verify(request):
    """
    사용자가 회원 정보 페이지에 접근하거나, 회원 탈퇴를 요청하면
    한번 더 비밀번호 인증을 받는 함수입니다.

    Args:
        request: 사용자의 요청 객체

    Returns:
        - POST 요청일 경우, 사용자가 입력한 비밀번호를 토대로 새로운 인증 세션을 생성합니다.
        - GET 요청일 경우, 비밀번호 입력 페이지를 render 합니다.
    """
    # 항상 새 인증을 위해 이전 세션 삭제
    request.session.pop("password_verified", None)

    # 다음 목적지를 기본적으로 update 페이지로 설정합니다.
    # 만약 next 값이 들어오지 않았다면 next를 accounts:update로 두겠다는 설정입니다.
    next_url = request.GET.get("next", reverse("accounts:update"))

    if request.method == "POST":
        # DB에 저장된 사용자 정보에 인증을 시도하기 위해
        # 사용자가 입력한 비밀번호를 변수에 할당합니다.
        password = request.POST.get("password")
        # DB에 저장되어있는 username을 불러오고 authenticate 함수를 통해
        # 사용자에게 입력받은 비밀번호로 인증을 시도합니다.
        # 인증되었다면 해당 사용자 객체를 반환하고 인증되지 않는다면 None을 반환합니다.
        user = authenticate(username=request.user.username, password=password)

        # 인증되었다면 세션이 인증 상태를 저장합니다.
        if user is not None:
            # 인증을 한 시간을 체크합니다.
            # update 함수에서 시간이 지나면 인증이 만료되도록 처리합니다.
            request.session["password_verified"] = timezone.now().timestamp()

            # 목적지가 결정되지 않았다면 update, 결정되었다면 결정된 페이지로 리다이렉트합니다.
            return redirect(next_url)
        # 인증되지 않았다면 error를 context에 담아 반환합니다.
        else:
            context = {"error": "비밀번호가 올바르지 않습니다."}
            return render(request, "accounts/verify.html", context)

    return render(request, "accounts/verify.html")
