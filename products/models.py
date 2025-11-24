from django.db import models

from accounts.models import User


# Create your models here.
class FinProduct(models.Model):
    id = models.AutoField(primary_key=True)
    company_type = models.CharField(max_length=50)
    company_name = models.CharField(max_length=100)
    product_name = models.CharField(max_length=200)
    product_code = models.CharField(max_length=50)
    maturity_interest = models.TextField(blank=True, default="")
    conditions = models.TextField(blank=True, default="")
    join_method = models.CharField(max_length=255, blank=True, default="")
    join_target = models.CharField(max_length=255, blank=True, default="")
    max_limit = models.CharField(max_length=255, blank=True, default="")
    disclosure_start = models.CharField(max_length=20, blank=True, default="")
    disclosure_end = models.CharField(max_length=20, blank=True, default="")
    disclosure_month = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        managed = False  # 기존 테이블 참조용(Django가 CREATE 안 함)
        db_table = "fin_products"

    def __str__(self):
        return self.product_name


class FavoriteProduct(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    product = models.ForeignKey(FinProduct, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorite_products"
