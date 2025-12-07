from django.urls import path

from . import views


app_name = "products"

urlpatterns = [
    path("", views.index, name="index"),
    path("search/", views.search, name="search"),
    path("detail/<str:fin_prdt_cd>/", views.product_detail, name="product_detail"),
]
