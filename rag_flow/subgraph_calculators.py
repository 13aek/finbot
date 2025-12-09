# calculator_graph.py
import json
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from finbot.singleton.ai_client import ai_client
from findata.config_manager import JsonConfigManager
from rag_flow.calculators import calculator_fixed_deposit, calculator_installment_deposit, calculator_jeonse_loan
from rag_flow.decorators import timing_decorator


# from rag_flow.graph_flow import ChatState


BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "findata" / "config.json"
jm = JsonConfigManager(path=config_path)
config = jm.values.tags
calculator_config = jm.values.calculator


class CalcState(TypedDict, total=False):
    product_data: dict  # calculator에 넘겨줄 상품 데이터
    category: Literal["fixed_deposit", "installment_deposit", "jeonse_loan"]
    data_columns: list  # product_data의 컬럼들 모음
    calculator_columns: list  # calculator에 필요한 컬럼들 (카테고리별로 상이)

    calculator_data: dict  # calculator에 쓸 데이터
    calculated_data: dict  # 계산된 데이터
    need_human_data: str


@timing_decorator
def check_findata(state: CalcState) -> CalcState:
    """
    데이터 확인 후 다음 단계 결정
    process_findata : findata를 받았으면 data 기반으로 계산
    process_endtoend : data가 없으면 필요한 데이터를 받아서 계산

    parameter (State) : graph state (부모 State 상속)
    return (Command) : Literal["process_findata", "process_endtoend"]
    """
    # print("*"*10,"product data : ",state["product_data"])
    if state["product_data"]:
        cat_dict = {
            "정기예금": "fixed_deposit",
            "적금": "installment_deposit",
            "전세자금대출": "jeonse_loan",
        }
        category = cat_dict[state["product_data"]["상품카테고리"]]
        data_columns = list(config[category].values())
        calculator_columns = calculator_config[category]
        calculator_method = "using_recommended_data"
        return {
            "calculator_method": calculator_method,
            "category": category,
            "data_columns": data_columns,
            "calculator_columns": calculator_columns,
        }
    else:
        calculator_method = "using_only_user_input_data"
        return {
            "calculator_method": calculator_method,
        }
    #     return Command(
    #         goto="fill_calculator_data",
    #         update= {
    #             "category" : category,
    #             "data_columns" : data_columns,
    #             "calculator_columns" : calculator_columns,
    #         }
    #         )

    # else:
    #     return Command(
    #         goto="conditional_about_fin_type",
    #         )


def calculator_method_router(
    state: CalcState,
) -> Literal["using_recommended_data", "using_only_user_input_data"]:
    """
    Search Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["recommend_mode", "calculate_mode", "explain_mode", "normal_mode"] 중 하나의 값으로 제한
    """
    return state["calculator_method"]


@timing_decorator
def conditional_about_fin_type(state: CalcState) -> CalcState:
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
        {"role": "user", "content": f"다음은 '4가지 경우야':\n{four_branch}"},
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


@timing_decorator
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
            calculator_data = {key: None for key in state["calculator_columns"]}
            for key in data.keys():
                if key in calculator_columns:
                    calculator_data[key] = data[key]
                else:
                    continue
            for option in data["옵션"]:
                for key in option.keys():
                    if key in calculator_columns:
                        if calculator_data[key] is None:
                            calculator_data[key] = []
                        if isinstance(calculator_data[key], list):
                            calculator_data[key].append(option[key])
                        else:
                            # 이미 단일 값이 있으면 리스트로 승격
                            calculator_data[key] = [calculator_data[key], option[key]]
                    else:
                        continue
        else:
            print(f"계산 가능한 {category}옵션이 없습니다")

        return {"calculator_data": calculator_data, "need_user_feedback": True}


@timing_decorator
def check_need_data(state: CalcState) -> CalcState:
    """
    calculator_data에서 비어 있는 컬럼(=사용자에게 물어봐야 할 값)을 찾고,
    - 있으면: need_user_feedback=True, need_columns 설정 후 여기서 END (subgraph 종료)
    - 없으면: category에 따라 어떤 계산 노드로 갈지 parent가 판단할 수 있도록 플래그만 세팅
    """
    calculator_data = state.get("calculator_data", {})
    need_columns = []

    for key, value in calculator_data.items():
        if value in (None, "", []):
            need_columns.append(key)

    if need_columns:
        # 🟥 아직 부족한 데이터가 있어서, 여기서 subgraph를 멈출 것임
        return {
            "need_user_feedback": True,
            "need_columns": need_columns,
        }
    else:
        # 🟩 이제 계산 가능 → 어떤 계산을 할지 category로 parent가 분기하게 둔다
        return {
            "need_user_feedback": False,
            "need_columns": [],
        }


@timing_decorator
def user_feedback(state: CalcState) -> CalcState:
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
        if key == "최고한도":
            continue
        if calculator_data[key]:
            continue
        else:
            need_columns.append(key)
    feedback = ", ".join(need_columns)
    if need_columns:
        human_text = interrupt(f"{feedback}에 대한 입력이 필요합니다. 정보를 알려주시면 계산해드릴게요.")
        loop_or_not_method = "get_user_data"
        return {
            "query": human_text,
            "need_user_feedback": False,
            "loop_or_not_method": loop_or_not_method,
        }
        # return Command(
        #     goto="get_user_data",
        #     update= {
        #         "query": human_text,
        #         "need_user_feedback": False
        #     }
        # )

    else:
        if category == "fixed_deposit":
            loop_or_not_method = "calc_fixed_deposit"
            return {
                "loop_or_not_method": loop_or_not_method,
            }
            # return Command(
            #     goto="calc_fixed_deposit"
            # )
        elif category == "installment_deposit":
            loop_or_not_method = "calc_installment_deposit"
            return {
                "loop_or_not_method": loop_or_not_method,
            }
            # return Command(
            #     goto="calc_installment_deposit"
            # )
        elif category == "jeonse_loan":
            loop_or_not_method = "calc_jeonse_loan"
            return {
                "loop_or_not_method": loop_or_not_method,
            }
            # return Command(
            #     goto="calc_jeonse_loan"
            # )


def loop_or_not_method_router(
    state: CalcState,
) -> Literal[
    "get_user_data",
    "calc_fixed_deposit",
    "calc_installment_deposit",
    "calc_jeonse_loan",
]:
    """
    Loop Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["get_user_data", "calc_fixed_deposit", "calc_installment_deposit", "calc_jeonse_loan"]
        중 하나의 값으로 제한
    """
    return state["loop_or_not_method"]


class FixedDeposit(BaseModel):
    납입액: int
    우대조건: str
    최고한도: int
    저축개월: int
    저축금리유형명: str
    저축금리: float
    최고우대금리: float


class InstallmentDeposit(BaseModel):
    납입액: int
    우대조건: str
    최고한도: int
    저축개월: int
    저축금리유형명: str
    저축금리: float
    최고우대금리: float


class JeonseLoan(BaseModel):
    대출액: int
    대출한도: str
    대출금리유형: str
    대출금리최저: float
    대출금리최고: float


@timing_decorator
def get_user_data(state: CalcState) -> CalcState:
    """
    query로 계산에 필요한 정보 추출

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Command
    """

    user_query = state["query"]
    calculator_data = state["calculator_data"]
    messages = [
        {
            "role": "system",
            "content": "너는 사용자 입력을 보고 정보를 추출해서 데이터에 채워넣어야해.",
        },
        {"role": "user", "content": f"다음은 '데이터'야:\n{calculator_data}"},
        {
            "role": "user",
            "content": (
                f"사용자 입력: {user_query}\n을 보고 '데이터'의 빈곳을 채워줘."
                "데이터'가 이미 채워진 곳은 수정하면 안돼."
                "돈 관련 입력은 '원' 단위로 환산해서 integer 타입으로 변환해야해."
                "만약 '데이터'의 빈 곳에 맞는 정보가 없으면 None 타입을 채워넣어."
                "다른 설명은 필요없고 데이터의 빈곳을 채운 새 데이터를 format에 맞춰서 반환해줘."
            ),
        },
    ]
    text_format = {
        "fixed_deposit": FixedDeposit,
        "installment_deposit": InstallmentDeposit,
        "jeonse_loan": JeonseLoan,
    }
    category = state["category"]

    completion = ai_client.responses.parse(
        model="gpt-4o-mini",
        input=messages,
        # JSON 스키마 지정
        text_format=text_format[category],
    )

    answer = json.loads(completion.output_text)

    # need_columns = []
    # for key in answer.keys():
    #     if answer[key]:
    #         continue
    #     else:
    #         need_columns.append(key)

    # 논리 오류. json output을 강제 했기 때문에 사용자가 입력을 하지 않아도
    # 강제된 입력 형식을 맞춰서 채워넣었을 가능성이 있음.
    # 추후 확인 해봐야함.
    return {
        "calculator_data": answer,
    }

    # if need_columns:
    #     return Command(
    #         goto="user_feedback",
    #         update= {
    #             "calculator_data": answer,
    #             "need_user_feedback": True
    #         }
    #     )

    # else:
    #     if category == "fixed_deposit":
    #         return Command(
    #             goto="calc_fixed_deposit",
    #             update= {
    #             "calculator_data": answer,
    #             "need_user_feedback": False
    #         }
    #         )
    #     if category == "installment_deposit":
    #         return Command(
    #             goto="calc_installment_deposit",
    #             update= {
    #             "calculator_data": answer,
    #             "need_user_feedback": False
    #         }
    #         )
    #     if category == "jeonse_loan":
    #         return Command(
    #             goto="calc_jeonse_loan",
    #             update= {
    #             "calculator_data": answer,
    #             "need_user_feedback": False
    #         }
    #         )


@timing_decorator
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
        "calculated_data": calculated_data,
    }


@timing_decorator
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
        "calculated_data": calculated_data,
    }


@timing_decorator
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
        "calculated_data": calculated_data,
    }


@timing_decorator
def after_calculate(state: CalcState) -> CalcState:
    """

    return : dict,
    """

    return {
        "answer": state["calculated_data"],
    }


def build_calculator_subgraph():
    graph = StateGraph(CalcState)

    # 노드 등록
    graph.add_node("check_findata", check_findata)
    graph.add_node("fill_calculator_data", fill_calculator_data)
    graph.add_node("conditional_about_fin_type", conditional_about_fin_type)
    graph.add_node("user_feedback", user_feedback)
    graph.add_node("get_user_data", get_user_data)
    graph.add_node("calc_fixed_deposit", calc_fixed_deposit)
    graph.add_node("calc_installment_deposit", calc_installment_deposit)
    graph.add_node("calc_jeonse_loan", calc_jeonse_loan)

    # 시작 → route
    # graph.add_edge(START, "check_findata")
    # graph.add_edge("check_findata", "fill_calculator_data")
    # # 주어진 데이터가 없을 때 분기. 아직 구현하지 않음
    # graph.add_edge("check_findata", "conditional_about_fin_type")

    # graph.add_edge("fill_calculator_data", "user_feedback")
    # # 데이터 받기
    # graph.add_edge("user_feedback", "get_user_data")
    # # 각 계산 노드 → END
    # graph.add_edge("user_feedback", "calc_fixed_deposit")
    # graph.add_edge("user_feedback", "calc_installment_deposit")
    # graph.add_edge("user_feedback", "calc_jeonse_loan")
    # # 필요한 데이터가 없을 때 loop
    # graph.add_edge("get_user_data", "user_feedback")
    # # 각 계산 노드 → END
    # graph.add_edge("get_user_data", "calc_fixed_deposit")
    # graph.add_edge("get_user_data", "calc_installment_deposit")
    # graph.add_edge("get_user_data", "calc_jeonse_loan")

    # graph.add_edge("calc_fixed_deposit", END)
    # graph.add_edge("calc_installment_deposit", END)
    # graph.add_edge("calc_jeonse_loan", END)

    graph.add_edge(START, "check_findata")

    graph.add_edge("fill_calculator_data", "user_feedback")

    graph.add_edge("calc_fixed_deposit", END)
    graph.add_edge("calc_installment_deposit", END)
    graph.add_edge("calc_jeonse_loan", END)

    return graph.compile()
