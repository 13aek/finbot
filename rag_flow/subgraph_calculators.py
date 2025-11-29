# calculator_graph.py
from typing import Literal, TypedDict
from pathlib import Path
from langgraph.types import Command, interrupt
from langgraph.graph import END, START, StateGraph

from findata.config_manager import JsonConfigManager
from rag_flow.calculators import (
    calculator_fixed_deposit, 
    calculator_installment_deposit,
    calculator_jeonse_loan,
)


BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "findata" / "config.json"
jm = JsonConfigManager(path=config_path)
config = jm.values.tags
calculator_config = jm.values.calculator


class CalcState(TypedDict, total=False):
    
    
    product_data: dict  # calculator에 넘겨줄 상품 데이터
    catetory: Literal["fixed_deposit", "installment_deposit", "jeonse_loan"]
    data_columns: list # product_data의 컬럼들 모음
    calculator_columns: list #calculator에 필요한 컬럼들 (카테고리별로 상이)

    calculator_data: dict # calculator에 쓸 데이터
    calculated_data: dict # 계산된 데이터
    need_human_data: str

    # 계산 결과
    # interest_before_tax: float
    # result_before_tax: float  # 예금/적금: 만기 총액, 대출: 총 상환액
    # tax_amount: float
    # result_after_tax: float  # 예금/적금: 세후 수령액, 대출: 세후(여기선 동일)

def check_findata(state: CalcState) -> Command[Literal["process_findata", "process_endtoend"]]:
    """
    데이터 확인 후 다음 단계 결정
    process_findata : findata를 받았으면 data 기반으로 계산
    process_endtoend : data가 없으면 필요한 데이터를 받아서 계산

    parameter (State) : graph state (부모 State 상속)
    return (Command) : Literal["process_findata", "process_endtoend"]
    """
    if state["product_data"]:
        category = state["product_data"]["상품카테고리"]
        data_columns = list(config[category].values())
        calculator_columns = calculator_config[category]

        return Command(
            goto="fill_calculator_data",
            update= {
                "category" : category,
                "data_columns" : data_columns,
                "calculator_columns" : calculator_columns,
            }
            )

    else:
        return Command(
            goto="conditional_about_fin_type",
            )
    
def conditional_about_fin_type(state: CalcState) -> Command[Literal["fixed_deposit", "installment_deposit", "jeonse_loan", "else"]]:
    """
    query에 따라 분기 발생. user의 의도에 따라 4가지로 분기.
    1. fixed_deposit
    2. installment_deposit
    3. jeonse_loan
    4. else

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 method dict,
                agent_method = ("fixed_deposit", "installment_deposit", "jeonse_loan", "else")
    """
    four_branch = (
        "fixed_deposit : 질문의 의도가 예금에 대한 작업을 원할 때 'fixed_deposit'를 반환"
        "installment_deposit : 질문의 의도가 적금에 대한 작업을 원할 때 'installment_deposit'를 반환"
        "jeonse_loan : 질문의 의도가 대출에 대한 작업을 원할 때, 'jeonse_loan'을 반환"
        "else : 위 세가지 의도가 담기지 않은 모든 경우에, 'else'을 반환"
    )
    user_query = state["query"]
    messages = [
        {
            "role": "system",
            "content": "너는 질문을 보고 목적을 생각해서 4가지 중에 하나로 분류 해야해.",
        },
        {   "role": "user", "content": f"다음은 '4가지 경우야':\n{four_branch}"},
        {
            "role": "user",
            "content": f"질문: {user_query}\n을 보고 4가지 경우 중 하나를 출력해줘. \
                다른 설명은 필요없고 recommend_mode, calculate_mode, explain_mode, normal_mode\
                    이 4가지 중에 무조건 하나를 반환해야해. 부연설명 붙이지 말고 마침표도 붙이지 마.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=400,
    )

    answer = completion.choices[0].message.content

    if answer in ["fixed_deposit", "installment_deposit", "jeonse_loan", "else"]:
        method = answer
    elif ("recommend" in answer) or ("rec" in answer) or ("추천" in answer):
        method = "recommend_mode"
    elif ("calculate" in answer) or ("calculator" in answer) or ("cal" in answer) or ("계산" in answer):
        method = "calculate_mode"
    elif (
        ("finword" in answer) or ("explain" in answer) or ("fin" in answer) or ("word" in answer) or ("설명" in answer)
    ):
        method = "explain_mode"
    else:
        method = "normal_mode"

    return {
        "agent_method": method,
    }



def fill_calculator_data(state: CalcState) -> CalcState:
    """
    calculator에 필요한 데이터 입력

    :param state: Description
    :type state: ChatState
    :return: Description
    :rtype: ChatState
    """
    
    if state["product_data"]:
        data = state["product_data"]
        calculator_columns = state["calculator_columns"]
        category = state["category"]
        if data.get("옵션"):
            calculator_data = { key: [] for key in state["calculator_columns"]}
            for key in data.keys():
                if key in calculator_columns:
                    calculator_data[key] = data[key]
                else: continue
            for option in data["옵션"]:
                for key in option.keys():
                    if key in calculator_columns:
                        calculator_data[key].append(data[key])
                    else:
                        continue
        else:
            print(f'계산 가능한 {category}옵션이 없습니다')

    return {"calculator_data": calculator_data, "need_user_feedback": True}



def human_feedback(state: CalcState) -> CalcState:
    """
    사용자에게 graph flow 중간에 피드백을 입력 받음

    :param state: Description
    :type state: ChatState
    :return: Description
    :rtype: ChatState
    """
    need_columns = []
    calculator_data = state["calculator_data"]
    category = state["category"]
    for key in calculator_data.keys():
        if calculator_data[key]:
            continue
        else:
            need_columns.append(key)
    feedback = ', '.join(need_columns)
    if need_columns:
        human_text = interrupt(f"{feedback}에 대한 입력이 필요합니다. 정보를 알려주시면 계산해드릴게요.")
        return Command(
            goto="get_human_data",
            update= {
                "query": human_text, 
                "need_user_feedback": False
            }
        )
            
    else:
        if category == "fixed_deposit":
            return Command(
                goto="calc_fixed_deposit"
            )
        if category == "installment_deposit":
            return Command(
                goto="calc_installment_deposit"
            )
        if category == "jeonse_loan":
            return Command(
                goto="calc_jeonse_loan"
            )
    



def calc_fixed_deposit(state: CalcState) -> CalcState:
    """

    return : dict, 
    {
        "상품카테고리": "fixed_deposit",
        "원금": int(principal),
        "세전이자": int(interest),
        "세전만기금액": int(maturity),
        "세금": int(tax),
        "세후수령액": int(maturity_after_tax),
        "적용금리(%)": annual_rate * 100,
        "기간(개월)": months,
        "이자방식": interest_type,
        "우대조건": data["우대조건"]
    }
    """
    calculated_data = calculator_fixed_deposit(state["calculator_data"])

    return {
        "calculated_data" : calculated_data,
    }


def calc_installment_deposit(state: CalcState) -> CalcState:
    """

    return : dict, 
    {
        "상품카테고리": "fixed_deposit",
        "원금": int(principal),
        "세전이자": int(interest),
        "세전만기금액": int(maturity),
        "세금": int(tax),
        "세후수령액": int(maturity_after_tax),
        "적용금리(%)": annual_rate * 100,
        "기간(개월)": months,
        "이자방식": interest_type,
        "우대조건": data["우대조건"]
    }
    """
    calculated_data = calculator_installment_deposit(state["calculator_data"])

    return {
        "calculated_data" : calculated_data,
    }


def calc_jeonse_loan(state: CalcState) -> CalcState:
    """

    return : dict, 
    {
        "상품카테고리": "fixed_deposit",
        "원금": int(principal),
        "세전이자": int(interest),
        "세전만기금액": int(maturity),
        "세금": int(tax),
        "세후수령액": int(maturity_after_tax),
        "적용금리(%)": annual_rate * 100,
        "기간(개월)": months,
        "이자방식": interest_type,
        "우대조건": data["우대조건"]
    }
    """
    calculated_data = calculator_jeonse_loan(state["calculator_data"])

    return {
        "calculated_data" : calculated_data,
    }


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
