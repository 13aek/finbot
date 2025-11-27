from django.db import models


# # Create your models here.
# class FinProduct(models.Model):
#     id = models.AutoField(primary_key=True)
#     company_type = models.CharField(max_length=50)
#     company_name = models.CharField(max_length=100)
#     product_name = models.CharField(max_length=200)
#     product_code = models.CharField(max_length=50)
#     maturity_interest = models.TextField(blank=True, default="")
#     conditions = models.TextField(blank=True, default="")
#     join_method = models.CharField(max_length=255, blank=True, default="")
#     join_target = models.CharField(max_length=255, blank=True, default="")
#     max_limit = models.CharField(max_length=255, blank=True, default="")
#     disclosure_start = models.CharField(max_length=20, blank=True, default="")
#     disclosure_end = models.CharField(max_length=20, blank=True, default="")
#     disclosure_month = models.CharField(max_length=10, blank=True, default="")

#     class Meta:
#         managed = False  # 기존 테이블 참조용(Django가 CREATE 안 함)
#         db_table = "fin_products"

#     def __str__(self):
#         return self.product_name

# orm 조회를 위한 임시 모델 생성


class FinProduct(models.Model):
    fin_prdt_cd = models.CharField(max_length=50, primary_key=True)  # PK
    kor_co_nm = models.CharField(max_length=100, blank=True, null=True)
    fin_co_no = models.CharField(max_length=50, blank=True, null=True)
    fin_prdt_nm = models.CharField(max_length=200, blank=True, null=True)
    join_way = models.CharField(max_length=255, blank=True, null=True)
    company_type = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)

    # DB에서 varchar(20)이므로 DateField 사용하면 안됨
    dcls_strt_day = models.CharField(max_length=20, blank=True, null=True)
    dcls_end_day = models.CharField(max_length=20, blank=True, null=True)
    dcls_month = models.CharField(max_length=20, blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False  # 기존 테이블 사용
        db_table = "fin_products"

    def __str__(self):
        return self.fin_prdt_nm or ""
