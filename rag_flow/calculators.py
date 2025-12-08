def calculator_fixed_deposit(data: dict, use_favor: bool = False):
    """
    정기예금(거치식) 계산 함수
    data 예시:
    {
        "납입액": 200000,
        "우대조건" : "",
        "최고한도" : 300000,
        "저축개월" : 12,
        "저축금리유형명" : "복리" or "단리",
        "저축금리" : 2.4,
        "최고우대금리" : 4.5,
    }
    use_favor=True → 최고우대금리 적용
    """

    principal = data["납입액"]
    months = data["저축개월"]
    tax_rate = 0.154

    # 금리 결정
    if use_favor:
        annual_rate = data["최고우대금리"] / 100
    else:
        annual_rate = data["저축금리"] / 100

    # 금리 방식
    interest_type = data["저축금리유형명"]

    # 계산
    if interest_type == "단리":
        # 단리 계산
        interest = principal * annual_rate * (months / 12)
        maturity = principal + interest

    elif interest_type == "복리":
        # 복리 계산
        monthly_rate = annual_rate / 12
        maturity = principal * ((1 + monthly_rate) ** months)
        interest = maturity - principal

    else:
        interest_type = "단리"
        # raise ValueError("저축금리유형명은 '단리' 또는 '복리'여야 합니다.")

    # 세금
    tax = interest * tax_rate
    maturity_after_tax = maturity - tax

    return {
        "상품카테고리": "fixed_deposit",
        "원금": int(principal),
        "세전이자": int(interest),
        "세전만기금액": int(maturity),
        "세금": int(tax),
        "세후수령액": int(maturity_after_tax),
        "적용금리(%)": annual_rate * 100,
        "기간(개월)": months,
        "이자방식": interest_type,
        "우대조건": data["우대조건"],
    }


def calculator_installment_deposit(data: dict, use_favor: bool = False):
    """
    정액적립식 적금 단리 / 복리 통합 계산기

    data 예시:
    {
        "납입액":200000,
        "우대조건": "",
        "최고한도" : 300000,
        "저축개월": 12,
        "저축금리유형명": "단리" 또는 "복리",
        "저축금리" : 2.4,
        "최고우대금리" : 4.5
    }

    use_favor=True → 최고우대금리 적용
    """

    monthly = data["납입액"]
    months = data["저축개월"]
    if data["저축금리유형명"]:
        interest_type = data["저축금리유형명"]
    else:
        interest_type = "복리"

    # 금리 선택 (기본/우대)
    if use_favor:
        annual_rate = data["최고우대금리"] / 100
    else:
        annual_rate = data["저축금리"] / 100

    # 총 원금
    total_principal = monthly * months

    # ---------------------------
    # 단리 적금 공식
    # ---------------------------
    # 이자 = A * r * (n(n+1)/2) / 12
    if interest_type == "단리":
        interest = monthly * annual_rate * (months * (months + 1) / 2) / 12
        maturity_before_tax = total_principal + interest

    # ---------------------------
    # 복리 적금 공식 (정확한 적금 복리 공식)
    # ---------------------------
    # 만기금 = A * { ((1+r/12)^n - 1) / (r/12) } * (1+r/12)
    elif interest_type == "복리":
        monthly_rate = annual_rate / 12

        if monthly_rate == 0:  # 금리가 0일 때
            maturity_before_tax = total_principal
        else:
            maturity_before_tax = (
                monthly
                * ((1 + monthly_rate) ** months - 1)
                / monthly_rate
                * (1 + monthly_rate)
            )

        interest = maturity_before_tax - total_principal

    else:
        raise ValueError("저축금리유형명은 '단리' 또는 '복리'여야 합니다.")

    # ---------------------------
    # 세금 적용 (이자 * 15.4%)
    # ---------------------------
    tax_rate = 0.154
    tax = interest * tax_rate
    maturity_after_tax = maturity_before_tax - tax

    return {
        "상품카테고리": "installment_deposit",
        "원금": int(total_principal),
        "세전이자": int(interest),
        "세전만기금액": int(maturity_before_tax),
        "세금": int(tax),
        "세후수령액": int(maturity_after_tax),
        "적용금리(%)": annual_rate * 100,
        "기간(개월)": months,
        "이자방식": interest_type,
        "우대조건": data["우대조건"],
    }


def calculator_jeonse_loan(data: dict, use_max_rate: bool = False):
    """
    전세대출 월 이자 계산 함수
    data 예시:
    {
        "대출액": 200000000,
        "대출한도": 220000000,
        "대출금리유형": "변동금리" or "고정금리",
        "대출금리최저": 2.78,
        "대출금리최고": 7.09,
    }

    use_max_rate=False → 최저금리 사용
    use_max_rate=True  → 최고금리 사용
    """

    loan_amount = data["대출액"]
    rate_type = data["대출금리유형"]
    if rate_type not in ["고정금리", "변동금리"]:
        rate_type = "고정금리"

    # ----------------------
    # 금리 선택
    # ----------------------
    if rate_type == "고정금리":
        # 고정금리는 최저/최고 개념이 없다고 가정 → 최저금리를 사용
        annual_rate = data["대출금리최저"] / 100

    elif rate_type == "변동금리":
        if use_max_rate:
            annual_rate = data["대출금리최고"] / 100
        else:
            annual_rate = data["대출금리최저"] / 100
    else:
        raise ValueError("대출금리유형은 '고정금리' 또는 '변동금리'여야 합니다.")

    # ----------------------
    # 월 이자 계산
    # ----------------------
    monthly_interest = loan_amount * annual_rate / 12

    return {
        "상품카테고리": "jeonse_loan",
        "대출금리유형": rate_type,
        "적용금리(%)": annual_rate * 100,
        "대출액": int(loan_amount),
        "월이자": int(monthly_interest),
        "연간이자": int(monthly_interest * 12),
    }
