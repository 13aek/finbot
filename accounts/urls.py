from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.test, name="test"),
    path("signup/", views.signup, name="signup"),
]
