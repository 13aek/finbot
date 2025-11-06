from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.test, name="test"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("update/", views.update, name="update"),
    path("password/", views.password, name="password"),
    path("logout/", views.logout, name="logout"),
    path("delete/", views.delete, name="delete"),  # 계정 삭제 추가
    path("verify/", views.verify, name="verify"),  # 비밀번호 추가 인증 url 추가
]
