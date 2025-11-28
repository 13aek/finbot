from django.db import models


# 1. FinProduct (금융상품 기본 정보)
# 금융상품 기본정보 테이블에 대한 Upsert 로직 담당
class FinProductManager(models.Manager):
    """
    금융위 baseList 데이터를 기반으로 금융상품(FinProduct)을 저장

    기능: upsert_from_api()
        - 상품코드(fin_prdt_cd)를 기준으로 DB에서 기존 레코드가 존재하면 UPDATE
        - 존재하지 않으면 INSERT
        - 즉, '중복 저장 방지 + 자동 업데이트' 로직 구현
    """

    def upsert_from_api(self, base: dict, *, description: str | None = None):
        fin_prdt_cd = base["fin_prdt_cd"]

        desc_value = description if description is not None else base.get("description")

        defaults = {
            "kor_co_nm": base.get("kor_co_nm"),
            "fin_co_no": base.get("fin_co_no"),
            "fin_prdt_nm": base.get("fin_prdt_nm"),
            "join_way": base.get("join_way"),
            "company_type": base.get("company_type"),
            "category": base.get("category"),
            "dcls_strt_day": base.get("dcls_strt_day"),
            "dcls_end_day": base.get("dcls_end_day"),
            "dcls_month": base.get("dcls_month"),
            "description": desc_value,
        }

        obj, created = self.update_or_create(
            fin_prdt_cd=fin_prdt_cd,
            defaults=defaults,
        )
        return obj, created


class FinProduct(models.Model):
    """
    금융위 '금융상품한눈에' baseList의 공통 필드를 보관

    모든 상품(예금/적금/전세자금대출)의 공통 메타 정보를 담는 '상품 마스터 테이블' 역할
    """

    fin_prdt_cd = models.CharField(max_length=50, primary_key=True)  # 기본 식별자(PK)
    kor_co_nm = models.CharField(max_length=100, null=True)  # 금융회사 정보
    fin_co_no = models.CharField(max_length=50, null=True)  # 금융회사 정보
    fin_prdt_nm = models.CharField(max_length=200, null=True)  # 상품명

    join_way = models.CharField(max_length=255, null=True)  # 가입방법

    company_type = models.CharField(max_length=50, null=True)  # 회사유형
    category = models.CharField(max_length=50, null=True)  # 카테고리

    dcls_strt_day = models.CharField(max_length=20, null=True)  # 공시 시작일
    dcls_end_day = models.CharField(max_length=20, null=True)  # 공시 종료일
    dcls_month = models.CharField(max_length=20, null=True)  # 공시 월

    description = models.TextField(null=True)  # 상품 설명

    objects = FinProductManager()  # Upsert 기능을 가진 Manager 연결

    class Meta:
        managed = True
        db_table = "fin_products"

    def __str__(self):
        return f"{self.fin_prdt_nm} ({self.fin_prdt_cd})"


# 2. FixedDepositOption (정기예금 옵션)
class FixedDepositOptionManager(models.Manager):
    """
    정기예금 옵션 테이블에 대한 Upsert 기능 적용

    중복판단 기준:
    - fin_prdt_cd           (상품코드)
    - intr_rate_type_nm     (금리유형)
    - save_trm              (기간)
    - dcls_month            (공시월)

    이 조합이 동일하면 '같은 옵션'으로 간주 → UPDATE 수행.
    그렇지 않으면 새로운 옵션으로 INSERT.
    """

    def upsert_from_api(self, base: dict, option: dict):
        """
        baseList + optionList 한 줄을 받아서 upsert
        """

        lookup = dict(  # Unique 판단 기준 (중복판단기준)
            fin_prdt_cd=base["fin_prdt_cd"],
            intr_rate_type_nm=option.get("intr_rate_type_nm"),
            save_trm=option.get("save_trm"),
            dcls_month=option.get("dcls_month") or base.get("dcls_month"),
        )

        # 업데이트될 필드
        defaults = {
            # baseList 필드
            "join_member": base.get("join_member"),
            "mtrt_int": base.get("mtrt_int"),
            "spcl_cnd": base.get("spcl_cnd"),
            "join_deny": base.get("join_deny"),
            "max_limit": base.get("max_limit"),
            "intr_rate": option.get("intr_rate"),
            "intr_rate2": option.get("intr_rate2"),
        }

        # ORM Upsert
        obj, created = self.update_or_create(
            **lookup,
            defaults=defaults,
        )
        return obj, created


class FixedDepositOption(models.Model):
    """
    정기예금 옵션 상세 데이터.
    1:N 관계에서 'N'에 해당하는 옵션 행(row)을 표현
    """

    id = models.AutoField(primary_key=True)

    # FK: fin_products.fin_prdt_cd
    fin_prdt_cd = models.ForeignKey(
        FinProduct,
        to_field="fin_prdt_cd",
        db_column="fin_prdt_cd",
        on_delete=models.CASCADE,
        related_name="fixed_options",
        db_index=True,
    )

    # baseList 비공통 필드
    join_member = models.CharField(max_length=255, null=True)
    mtrt_int = models.TextField(null=True)
    spcl_cnd = models.TextField(null=True)
    join_deny = models.CharField(max_length=10, null=True)
    max_limit = models.CharField(max_length=255, null=True)

    # optionList 필드
    intr_rate_type_nm = models.CharField(max_length=255, null=True)
    save_trm = models.CharField(max_length=255, null=True)
    intr_rate = models.TextField(null=True)
    intr_rate2 = models.TextField(null=True)
    dcls_month = models.CharField(max_length=20, null=True)

    objects = FixedDepositOptionManager()

    class Meta:
        managed = True
        db_table = "fixed_deposit_option"
        # DB 레벨에서 중복 방지 제약조건 설정
        constraints = [
            models.UniqueConstraint(
                fields=["fin_prdt_cd", "intr_rate_type_nm", "save_trm", "dcls_month"],
                name="uq_fixed_deposit_option_key",
            )
        ]

    def __str__(self):
        return f"[정기예금 옵션] {self.fin_prdt_cd_id} / {self.save_trm} / {self.intr_rate2}"


# 3. InstallmentDepositOption (적금 옵션)
class InstallmentDepositOptionManager(models.Manager):
    """
    적금 옵션 테이블 Upsert

    중복판단기준
    - fin_prdt_cd
    - rsrv_type_nm        (적립유형: 정액적립/자유적립 등)
    - intr_rate_type_nm
    - save_trm
    - dcls_month
    """

    def upsert_from_api(self, base: dict, option: dict):
        """
        (fin_prdt_cd, rsrv_type_nm, intr_rate_type_nm, save_trm, dcls_month) 기준 upsert
        """

        lookup = dict(
            fin_prdt_cd=base["fin_prdt_cd"],
            rsrv_type_nm=option.get("rsrv_type_nm"),
            intr_rate_type_nm=option.get("intr_rate_type_nm"),
            save_trm=option.get("save_trm"),
            dcls_month=option.get("dcls_month") or base.get("dcls_month"),
        )

        defaults = {
            "join_member": base.get("join_member"),
            "mtrt_int": base.get("mtrt_int"),
            "spcl_cnd": base.get("spcl_cnd"),
            "join_deny": base.get("join_deny"),
            "max_limit": base.get("max_limit"),
            "intr_rate": option.get("intr_rate"),
            "intr_rate2": option.get("intr_rate2"),
        }

        obj, created = self.update_or_create(
            **lookup,
            defaults=defaults,
        )
        return obj, created


class InstallmentDepositOption(models.Model):
    """
    적금 옵션 테이블
    - baseList 비공통 필드 + optionList 금리/기간 + 적립유형
    """

    id = models.AutoField(primary_key=True)

    # FK: fin_products.fin_prdt_cd
    fin_prdt_cd = models.ForeignKey(
        FinProduct,
        to_field="fin_prdt_cd",
        db_column="fin_prdt_cd",
        on_delete=models.CASCADE,
        related_name="installment_options",
        db_index=True,
    )

    join_member = models.CharField(max_length=255, null=True)
    mtrt_int = models.CharField(max_length=255, null=True)
    spcl_cnd = models.CharField(max_length=255, null=True)
    join_deny = models.CharField(max_length=10, null=True)
    max_limit = models.CharField(max_length=255, null=True)
    rsrv_type_nm = models.CharField(max_length=255, null=True)
    intr_rate_type_nm = models.CharField(max_length=255, null=True)
    save_trm = models.CharField(max_length=255, null=True)
    intr_rate = models.CharField(max_length=255, null=True)
    intr_rate2 = models.CharField(max_length=255, null=True)
    dcls_month = models.CharField(max_length=20, null=True)

    objects = InstallmentDepositOptionManager()

    class Meta:
        managed = True
        db_table = "installment_deposit_option"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "fin_prdt_cd",
                    "rsrv_type_nm",
                    "intr_rate_type_nm",
                    "save_trm",
                    "dcls_month",
                ],
                name="uq_installment_deposit_option_key",
            )
        ]

    def __str__(self):
        return f"[적금 옵션] {self.fin_prdt_cd_id} / {self.rsrv_type_nm} / {self.save_trm}"


# 4. JeonseLoanOption (전세자금대출 옵션)
class JeonseLoanOptionManager(models.Manager):
    """
    전세자금대출 옵션 테이블 Upsert

    중복판단기준
    - fin_prdt_cd
    - rpay_type_nm
    - lend_rate_type_nm
    - dcls_month
    """

    def upsert_from_api(self, base: dict, option: dict):
        lookup = dict(
            fin_prdt_cd=base["fin_prdt_cd"],
            rpay_type_nm=option.get("rpay_type_nm"),
            lend_rate_type_nm=option.get("lend_rate_type_nm"),
            dcls_month=option.get("dcls_month") or base.get("dcls_month"),
        )

        defaults = {
            # baseList 필드
            "loan_inci_expn": base.get("loan_inci_expn"),
            "erly_rpay_fee": base.get("erly_rpay_fee"),
            "dly_rate": base.get("dly_rate"),
            "loan_lmt": base.get("loan_lmt"),
            # optionList 필드
            "lend_rate_min": option.get("lend_rate_min"),
            "lend_rate_max": option.get("lend_rate_max"),
            "lend_rate_avg": option.get("lend_rate_avg"),
        }

        obj, created = self.update_or_create(
            **lookup,
            defaults=defaults,
        )
        return obj, created


class JeonseLoanOption(models.Model):
    """
    전세자금대출 옵션 테이블
    - baseList 비공통 필드 + optionList 금리/상환 유형
    """

    id = models.AutoField(primary_key=True)

    # FK: fin_products.fin_prdt_cd
    fin_prdt_cd = models.ForeignKey(
        FinProduct,
        to_field="fin_prdt_cd",
        db_column="fin_prdt_cd",
        on_delete=models.CASCADE,
        related_name="jeonse_options",
        db_index=True,
    )

    # baseList 전용 필드
    loan_inci_expn = models.TextField(null=True)
    erly_rpay_fee = models.TextField(null=True)
    dly_rate = models.TextField(null=True)
    loan_lmt = models.CharField(max_length=255, null=True)

    # optionList 필드
    rpay_type_nm = models.CharField(max_length=255, null=True)
    lend_rate_type_nm = models.CharField(max_length=255, null=True)
    lend_rate_min = models.TextField(null=True)
    lend_rate_max = models.TextField(null=True)
    lend_rate_avg = models.TextField(null=True)
    dcls_month = models.CharField(max_length=20, null=True)

    objects = JeonseLoanOptionManager()

    class Meta:
        managed = True
        db_table = "jeonse_loan_option"  # ← 여기 때문에 실제 테이블 이름이 이걸로 고정
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "fin_prdt_cd",
                    "rpay_type_nm",
                    "lend_rate_type_nm",
                    "dcls_month",
                ],
                name="uq_jeonse_loan_option_key",
            )
        ]

    def __str__(self):
        return f"[전세자금 옵션] {self.fin_prdt_cd_id} / {self.rpay_type_nm} / {self.lend_rate_type_nm}"
