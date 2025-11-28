# calculator_graph.py
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class CalcState(TypedDict, total=False):
    # 어떤 계산을 할지
    kind: Literal["deposit", "installment", "loan"]

    product_data: dict  # calculator에 넘겨줄 상품 데이터

    # 공통 파라미터
    rate: float  # 연 이자율 (예: 0.035 = 3.5%)
    month: float  # 기간(월 단위)
    tax_rate: float  # 이자소득세(15.4%면 0.154)

    # 예금 / 대출용
    principal: float  # 예금 원금 / 대출 원금

    # 적금용
    monthly: float  # 적금 월 납입액

    # 계산 결과
    interest_before_tax: float
    result_before_tax: float  # 예금/적금: 만기 총액, 대출: 총 상환액
    tax_amount: float
    result_after_tax: float  # 예금/적금: 세후 수령액, 대출: 세후(여기선 동일)


def calc_deposit(state: CalcState) -> CalcState:
    """
    예금: 단리 계산
    interest = principal * rate * years
    """

    product = state["product_data"]
    options = product["옵션"]
    # 옵션 하나 고정시키기
    # 최대 저축 개월, 최대 금리, 최저 금리 구하기
    max_save_trm = 0
    for idx, option in enumerate(options):
        if int(option["저축개월"]) > max_save_trm:
            max_idx = idx
            max_save_trm = int(option["저축개월"])

    option = options[max_idx]

    intr_rate_type_nm = options["저축금리유형명"]  # 단리 복리
    intr_rate_type_nm += intr_rate_type_nm
    principal = state["principal"]
    rate = state["rate"]
    years = state["years"]
    tax_rate = state.get("tax_rate", 0.154)

    interest = principal * rate * years
    gross = principal + interest
    tax = interest * tax_rate
    net = gross - tax

    return {
        "interest_before_tax": interest,
        "result_before_tax": gross,
        "tax_amount": tax,
        "result_after_tax": net,
    }


def calc_installment(state: CalcState) -> CalcState:
    """
    적금: 매월 동일 금액 납입, 단리 기준
    - 매월 납입액 monthly
    - 연이율 rate
    - 기간 years
    """
    monthly = state["monthly"]
    rate = state["rate"]
    years = state["years"]
    tax_rate = state.get("tax_rate", 0.154)

    months = int(years * 12)

    # 총 납입 원금
    total_principal = monthly * months

    # 단리 가정: 매월 납입 후 남은 개월 수 동안 이자 발생
    interest = 0.0
    monthly_rate = rate / 12
    for m in range(months):
        remaining_months = months - m
        interest += monthly * monthly_rate * remaining_months

    gross = total_principal + interest
    tax = interest * tax_rate
    net = gross - tax

    return {
        "interest_before_tax": interest,
        "result_before_tax": gross,
        "tax_amount": tax,
        "result_after_tax": net,
    }


def calc_loan(state: CalcState) -> CalcState:
    """
    대출: 원리금균등 상환
    - principal: 대출 원금
    - rate: 연 이자율
    - years: 기간(년)
    세금은 이자에 안 붙는다고 보고 tax_amount=0 처리
    """
    principal = state["principal"]
    rate = state["rate"]
    years = state["years"]

    months = int(years * 12)
    monthly_rate = rate / 12

    if monthly_rate == 0:
        monthly_payment = principal / months
    else:
        # 원리금균등 공식
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)

    total_payment = monthly_payment * months
    interest = total_payment - principal

    # 대출 이자는 세금 대상이 아니므로 0 처리
    tax = 0.0
    net = total_payment  # 세후/세전 동일

    return {
        "interest_before_tax": interest,
        "result_before_tax": total_payment,
        "tax_amount": tax,
        "result_after_tax": net,
    }


def route_kind(state: CalcState) -> dict:
    """
    kind 값(deposit/installment/loan)에 따라 분기
    add_conditional_edges에서 이 값을 그대로 사용.
    """
    return {"kind": state["kind"]}


def build_calculator_graph():
    graph = StateGraph(CalcState)

    # 노드 등록
    graph.add_node("route", route_kind)
    graph.add_node("deposit", calc_deposit)
    graph.add_node("installment", calc_installment)
    graph.add_node("loan", calc_loan)

    # 시작 → route
    graph.add_edge(START, "route")

    # route에서 kind에 따라 분기
    graph.add_conditional_edges(
        "route",
        lambda state: state["kind"],  # 반환값: "deposit" / "installment" / "loan"
        {
            "deposit": "deposit",
            "installment": "installment",
            "loan": "loan",
        },
    )

    # 각 계산 노드 → END
    graph.add_edge("deposit", END)
    graph.add_edge("installment", END)
    graph.add_edge("loan", END)

    return graph.compile()
