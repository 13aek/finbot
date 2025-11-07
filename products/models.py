from django.db import models


# Create your models here.
class FinProduct(models.Model):
    id = models.AutoField(primary_key=True)
    company_type = models.CharField(max_length=50)
    company_name = models.CharField(max_length=100)
    product_name = models.CharField(max_length=200)
    product_code = models.CharField(max_length=50)
    maturity_interest = models.TextField(null=True, blank=True)
    conditions = models.TextField(null=True, blank=True)
    join_method = models.CharField(max_length=255, null=True, blank=True)
    join_target = models.CharField(max_length=255, null=True, blank=True)
    max_limit = models.CharField(max_length=255, null=True, blank=True)
    disclosure_start = models.CharField(max_length=20, null=True, blank=True)
    disclosure_end = models.CharField(max_length=20, null=True, blank=True)
    disclosure_month = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        managed = False  # 기존 테이블 참조용(Django가 CREATE 안 함)
        db_table = "fin_products"

    def __str__(self):
        return self.product_name
