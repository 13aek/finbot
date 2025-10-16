from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.test, name="test"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("update/", views.update, name="update"),
]
