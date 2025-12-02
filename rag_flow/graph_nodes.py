import json
from functools import partial
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langgraph.types import interrupt
from pydantic import BaseModel

from finbot.singleton.ai_client import ai_client
from finbot.singleton.embedding_model import embed_model
from finbot.singleton.vectordb import qdrant_client
from findata.config_manager import JsonConfigManager
from rag_flow.calculators import (
    calculator_fixed_deposit,
    calculator_installment_deposit,
    calculator_jeonse_loan,
)
from rag_flow.decorators import error_handling_decorator, timing_decorator


BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "findata" / "config.json"
jm = JsonConfigManager(path=config_path)
config = jm.values.tags
calculator_config = jm.values.calculator


def keep_last_n(existing: list[dict], new: list[dict], n: int = 10) -> list[dict]:
    """
    최근 n개 항목만 유지하는 리듀서. State의 history List에 새로운 값을 추가하고 n개의 항목만 반환(유지)

    Args:
        existing (List[Dict]): 기존의 history List
        new (List[Dict]): 새로운 history List
    Returns:
        List[Dict][-n:]: 새로운 history List를 포함하여 n개의 항목 유지
    """
    combined = (existing or []) + (new or [])
    return combined[-n:]  # 마지막 n개만 반환


class ChatState(TypedDict, total=False):
    """
    graph를 구성할 State Class
    """

    visited: bool
    mode: Literal["first_hello", "Nth_hello", "agent_mode"]
    agent_method: Literal["rag_search", "calculator", "finword_explain", "normal_chat"]  # query의도에 따라 나뉘는 분기
    recommend_method: Literal["fixed_deposit", "installment_deposit", "jeonse_loan", "all"]
    recommend_mode: bool  # recommend 로직에 들어오게 되면 True
    query: str  # user query
    history: Annotated[list[dict[str, str]], partial(keep_last_n, n=10)]  # user, assistant message 쌍
    answer: str  # LLM answer
    user_feedback: str  # 사용자 중간 입력
    need_user_feedback: bool  # 사용자 입력 요청
    pos_or_neg: str  # 사용자 입력의 긍부정 판단
    product_code: str  # LLM이 추천하는 상품의 상품 코드
    product_data: dict  # calculator에 넘겨줄 상품 데이터

    # calculate datas
    calculator_method: Literal["fill_calculator_data", "conditional_about_fin_type"]  # 기존데이터 vs only 사용자입력
    category: Literal["fixed_deposit", "installment_deposit", "jeonse_loan"]
    loop_or_not_method: str  # 사용자 입력 루프
    feedback_or_not_method: str # 사용자 입력이 필요한지 구분
    data_columns: list  # product_data의 컬럼들 모음
    calculator_columns: list  # calculator에 필요한 컬럼들 (카테고리별로 상이)
    calculator_config: dict  # calculator config

    calculator_data: dict  # calculator에 쓸 데이터
    calculated_data: dict  # 계산된 데이터


# 노드 정의


@timing_decorator
@error_handling_decorator
def conditional_about_history(state: ChatState) -> dict:
    """
    history에 따라 분기 발생

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 mode dict, mode = ("first_hello", "Nth_hello", "agent_mode")
    """
    # 복합 조건 평가
    if not state["visited"]:
        mode = "first_hello"

    elif state["visited"]:
        if state["history"][-1]["state"] == "old":
            mode = "Nth_hello"

        elif state["history"][-1]["state"] == "new":
            mode = "agent_mode"

        else:
            print("Mode를 찾을 수 없습니다.")

    else:
        print("Mode를 찾을 수 없습니다.")

    return {
        "mode": mode,
        "product_data":None,
        "category": None,
    }


def mode_router(state: ChatState) -> Literal["first_hello", "Nth_hello", "agent_mode"]:
    """
    Mode에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["first_hello", "Nth_hello", "agent_mode"] 중 하나의 값으로 제한
    """
    return state["mode"]


@timing_decorator
@error_handling_decorator
def first_conversation(state: ChatState) -> ChatState:
    """
    이전 history 아예 없이 첫 방문 첫 인사

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 history dict.
    """

    answer = (
        "안녕하세요 🙂\n"
        "FinBot에 오신 걸 환영해요.\n"
        "예금·적금·전세대출 추천부터 수익·이자 계산까지\n"
        "금융 정보가 필요하시면 언제든 말씀해주세요!"
    ) 

    return {"answer": answer}


@timing_decorator
@error_handling_decorator
def nth_conversation(state: ChatState) -> ChatState:
    """
    이전 history 존재. 첫 인사.
    history 요약해서 제공

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 answer.
    """

    histories = state["history"]
    questions = [history["content"] for history in histories if history["role"] == "user"]

    messages = [
        {
            "role": "system",
            "content": "너는 주어지는 몇 개의 문장을 '3단어'로 요약해야해.",
        }
    ]
    messages.append({"role": "user", "content": f"다음은 주어진 문장들이야 :\n{questions}"})  # 이전 질문들 모두
    messages.append({"role": "user", "content": "주어진 문장들을 3단어로 요약해줘."})

    completion = ai_client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    summary = completion.choices[0].message.content

    answer = f"안녕하세요. 지난번에는 {summary} 등 에 대해 물어보셨군요! 오늘은 무엇을 도와드릴까요?"

    return {"answer": answer}


@timing_decorator
# @error_handling_decorator
def conditional_about_query(state: ChatState) -> dict:
    """
    query에 따라 분기 발생. user의 의도에 따라 4가지로 분기.
    1. 금융 상품 추천
    2. 계산기
    3. 금융 용어 상담
    4. 일반 채팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 method dict,
                agent_method = ("recommend", "calculator", "fin_word_explain", "normal_chat")
    """
    four_branch = (
        "recommend : 질문의 의미가 금융 상품에 대한 추천을 원하면 'recommend'를 반환"
        "calculator : 질문의 의미를 생각했을 때, 계산이 필요한 작업이 필요하면 'calculator'를 반환"
        "fin_word_explain : 금융 도메인에 대한 지식 이해를 위해 설명이 필요할 때, 'fin_word_explain'을 반환"
        "normal_chat : 위 세가지 의도가 담기지 않은 모든 경우에, 'normal_chat'을 반환"
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

    if answer in ["recommend_mode", "calculate_mode", "explain_mode", "normal_mode"]:
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


def agent_method_router(
    state: ChatState,
) -> Literal["recommend_mode", "calculate_mode", "explain_mode", "normal_mode"]:
    """
    Search Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["recommend_mode", "calculate_mode", "explain_mode", "normal_mode"] 중 하나의 값으로 제한
    """
    return state["agent_method"]


def db_search(state: ChatState) -> ChatState:
    """
    대화 히스토리를 프롬프트에 포함해 답변 생성

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 answer를 반환
    """

    db_answer = "DB 검색 결과"
    user_query = state["query"]
    messages = [
        {
            "role": "system",
            "content": "너는 금융 도메인 전문가이자 고객 상담 AI야. DB에서 제공된 정보를 근거로만 답변해야 해.",
        },
        {"role": "user", "content": f"다음은 DB에서 찾은 정보야:\n{db_answer}"},
        {
            "role": "user",
            "content": f"질문: {user_query}\n이 '정보'만 참고해서 사용자의 질문에 정확히 답변해줘.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=400,
    )

    answer = completion.choices[0].message.content
    return {"answer": answer}


@timing_decorator
# @error_handling_decorator
def conditional_about_recommend(state: ChatState) -> dict:
    """
    query에 따라 분기 발생. user의 의도에 따라 4가지로 분기.
    1. 예금 추천
    2. 적금 추천
    3. 대출 추천
    4. 그외 추천

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 method dict,
                agent_method = ("fixed_deposit", "installment_deposit", "jeonse_loan", "all")
    """
    four_branch = (
        "fixed_deposit : 질문의 의미가 예금 상품에 대한 정보를 원하면 'fixed_deposit'를 반환"
        "installment_deposit : 질문의 의미를 생각했을 때, 적금 상품에 대한 정보를 원하면 'installment_deposit'를 반환"
        "jeonse_loan : 질문의 의미가 대출 관련 상품에 대한 정보를 원하면, 'jeonse_loan'을 반환"
        "all : 위 세가지 의도가 담기지 않은 모든 경우에, 'all'을 반환"
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
                다른 설명은 필요없고 fixed_deposit, installment_deposit, jeonse_loan, all\
                    이 4가지 중에 무조건 하나를 반환해야해. 부연설명 붙이지 말고 마침표도 붙이지 마.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=400,
    )

    answer = completion.choices[0].message.content

    if answer in ["fixed_deposit", "installment_deposit", "jeonse_loan", "all"]:
        method = answer
    elif ("예금" in answer) or ("fix" in answer):
        method = "fixed_deposit"
    elif ("적금" in answer) or ("install" in answer):
        method = "installment_deposit"
    elif ("대출" in answer) or ("loan" in answer) or ("jeo" in answer):
        method = "jeonse_loan"
    else:
        method = "all"

    return {
        "recommend_method": method,
    }


def recommend_method_router(
    state: ChatState,
) -> Literal["fixed_deposit", "installment_deposit", "jeonse_loan", "all"]:
    """
    Search Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["fixed_deposit", "installment_deposit", "jeonse_loan", "all"] 중 하나의 값으로 제한
    """
    return state["recommend_method"]


@timing_decorator
# @error_handling_decorator
def rag_search(state: ChatState) -> ChatState:
    """
    사용자의 query와 유사한 RAG 결과를 생성하고, RAG 결과를 바탕으로 답변 반환

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 answer를 반환
    """

    topk = 3
    user_query = state["query"]
    q_vec = embed_model.encode([user_query], convert_to_numpy=True)[0]
    if state["recommend_method"] == "fixed_deposit":
        print("*" * 10, "예금 추천", "*" * 10)
        hits = qdrant_client.query_points(collection_name="finance_products_fixed_deposit", query=q_vec, limit=topk)
    elif state["recommend_method"] == "installment_deposit":
        print("*" * 10, "적금 추천", "*" * 10)
        hits = qdrant_client.query_points(
            collection_name="finance_products_installment_deposit", query=q_vec, limit=topk
        )
    elif state["recommend_method"] == "jeonse_loan":
        print("*" * 10, "대출 추천", "*" * 10)
        hits = qdrant_client.query_points(collection_name="finance_products_jeonse_loan", query=q_vec, limit=topk)
    else:
        print("*" * 10, "any 추천", "*" * 10)
        hits = qdrant_client.query_points(collection_name="finance_products_all", query=q_vec, limit=topk)

    vector_db_answer = hits.points[0].payload

    # messages = [
    #     {
    #         "role": "system",
    #         "content": (
    #             "너는 금융 도메인 전문가이자 고객 상담 AI야. vector_db에서 제공된 정보를 근거로만 답변해야 해."
    #             "마크다운 형식은 사용하지말고 단락을 잘 나눠서 출력해."
    #         ),
    #     },
    #     {
    #         "role": "user",
    #         "content": f"다음은 vector_db 정보야:\n{vector_db_answer}",
    #     },
    #     {
    #         "role": "user",
    #         "content": f"질문: {user_query}\n이 'vector_db 정보'만 참고해서 사용자의 질문에 정확히 답변해줘.",
    #     },
    # ]

    # completion = ai_client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=messages,
    #     max_tokens=600,
    #     # tools=
    # )
    # answer = completion.choices[0].message.content
    recommend_mode = True
    # 추천받은 상품을 view로 연결
    product_code = vector_db_answer["금융상품코드"]
    return {
        # "answer": answer,
        "recommend_mode": recommend_mode,
        "need_user_feedback": True,
        "product_code": product_code,
        "product_data": vector_db_answer,
    }


@timing_decorator
# @error_handling_decorator
def human_feedback(state: ChatState) -> ChatState:
    """
    사용자에게 graph flow 중간에 피드백을 입력 받음

    :param state: Description
    :type state: ChatState
    :return: Description
    :rtype: ChatState
    """

    human_text = interrupt("추천 상품에 대한 수익/이자 계산이 필요하신가요?")
    return {"query": human_text, "need_user_feedback": False}


@timing_decorator
# @error_handling_decorator
def classify_feedback(state: ChatState) -> ChatState:
    """
    사용자의 중간 feedback에 대한 긍, 부정 판단

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 answer를 반환
    """

    user_feedback = state["query"]
    print("classify_feedback input: ", user_feedback)
    messages = [
        {
            "role": "system",
            "content": (
                "지금은, user가 우리에게 '추천 상품에 대한 수익/이자 계산이 필요하신가요?' 라는 질문을 받고 우리에게 '답'을 해주는 상황이야."
                "너는 '답'을 보고 user가 우리에게 '계산을 원하는지' 유추해야해."
                "너는 한국어 '답'을 보고 '긍정', '부정'을 판단해야해."
                "긍정적인 맥락 혹은 뉘앙스면 '긍정', 부정적인 맥락이거나 유추를 못하겠다면 '부정'."
                "다른 말 하지말고 '긍정', '부정' 중에 한 단어만 출력해."
            ),
        },
        {
            "role": "user",
            "content": f"입력: {user_feedback}\n을 보고 yes, no 중에 한 단어만 출력해. 마침표도 필요없어.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=100,
    )
    pos_or_neg = completion.choices[0].message.content

    pos_word = ["yes", "sure", "긍정", "예", "맞", "그래", "응", "그렇", "긍정.", "'긍정'", "'긍정.'"]
    neg_word = ["no", "부정", "아니", "안", "no", "싫어", "왜", "부정.", "'부정'", "'부정.'"]
    if any([word in pos_or_neg for word in pos_word]):
        pos_or_neg = "yes"
    elif any([word in pos_or_neg for word in neg_word]):
        pos_or_neg = "no"
    print("classify_feedback output: ", pos_or_neg)
    return {"pos_or_neg": pos_or_neg}


def feedback_router(
    state: ChatState,
) -> Literal["yes", "no"]:
    """
    사용자 중간 feedback에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["yes", "no"] 중 하나의 값으로 제한
    """
    return state["pos_or_neg"]


@timing_decorator
# @error_handling_decorator
def before_calculate(state: ChatState) -> ChatState:
    """

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict:
    """
    state["need_user_feedback"] = True
    return state


# calculator = build_calculator_subgraph()


@timing_decorator
# @error_handling_decorator
def fin_word_explain(state: ChatState) -> ChatState:
    """

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict:
    """

    user_query = state["query"]

    messages = [
        {
            "role": "system",
            "content": (
                "너는 금융 도메인 전문가이자 고객 상담 AI야. user의 질문에 답해줘."
                "마크다운 형식은 사용하지말고 단락을 잘 나눠서 출력해."
            ),
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n 에 맞는 설명을 해줘.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=600,
    )
    answer = completion.choices[0].message.content

    return {"answer": answer}


@timing_decorator
# @error_handling_decorator
def normal_chat(state: ChatState) -> ChatState:
    """

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict:
    """

    user_query = state["query"]

    messages = [
        {
            "role": "system",
            "content": (
                "너는 금융 도메인 전문가이자 고객 상담 AI야. user의 질문에 상담사처럼 답해줘."
                "마크다운 형식은 사용하지말고 단락을 잘 나눠서 출력해."
            ),
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n에 답해줘.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=600,
    )
    answer = completion.choices[0].message.content

    return {"answer": answer}


@timing_decorator
# @error_handling_decorator
def add_to_history(state: ChatState) -> ChatState:
    """
    이전 대화 기록을 유지하면서 새 user message 추가

    Args:
        state (TypedDict): Graph의 state
    Returns:
        history (List[Dict]): state의 history update
        visited (bool): 방문 표시
    """
    new_history = []
    if state.get("query", False):
        new_history.append({"role": "user", "content": state["query"], "state": "new"})
        new_history.append({"role": "assistant", "content": state["answer"], "state": "new"})
    else:
        new_history.append({"role": "assistant", "content": state["answer"], "state": "new"})
    return {"history": new_history, "visited": True, "need_user_feedback": False}


@timing_decorator
def check_findata(state: ChatState) -> ChatState:
    """
    데이터 확인 후 다음 단계 결정
    process_findata : findata를 받았으면 data 기반으로 계산
    process_endtoend : data가 없으면 필요한 데이터를 받아서 계산

    parameter (State) : graph state (부모 State 상속)
    return (Command) : Literal["process_findata", "process_endtoend"]
    """

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
            "calculator_config": calculator_config,

        }


def calculator_method_router(
    state: ChatState,
) -> Literal["using_recommended_data", "using_only_user_input_data"]:
    """
    Search Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["using_recommended_data", "using_only_user_input_data"] 중 하나의 값으로 제한
    """
    return state["calculator_method"]


@timing_decorator
def using_only_user_input_data(state: ChatState) -> ChatState:
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
                다른 설명은 필요없고 fixed_deposit, installment_deposit, jeonse_loan, else\
                    이 4가지 중에 무조건 하나를 반환해야해. 부연설명 붙이지 말고 마침표도 붙이지 마.",
        },
    ]

    completion = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=400,
    )

    answer = completion.choices[0].message.content
    if answer != "else":
        if answer in ["fixed_deposit", "installment_deposit", "jeonse_loan", "else"]:
            method = answer
        elif ("fixed" in answer) or ("예금" in answer):
            method = "fixed_deposit"
        elif ("calculate" in answer) or ("calculator" in answer) or ("cal" in answer) or ("계산" in answer):
            method = "installment_deposit"
        elif (
            ("finword" in answer) or ("explain" in answer) or ("fin" in answer) or ("word" in answer) or ("설명" in answer)
        ):
            method = "jeonse_loan"
        
        calculator_columns = calculator_config[method]
        calculator_data = {key: None for key in calculator_columns}
        print('*'*10,f'{method} 계산')
        return {
            "category": method,
            "calculator_columns": calculator_columns,
            "calculator_data": calculator_data,
            "feedback_or_not_method": "pass",
        } 
        
    else:
        return {
            "feedback_or_not_method": "fill_fin_type",
        }

def feedback_or_not_method_router(
    state: ChatState,
) -> Literal["pass", "fill_fin_type"]:
    """
    Loop Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["pass", "fill_fin_type"]
        중 하나의 값으로 제한
    """
    return state["feedback_or_not_method"]

@timing_decorator
# @error_handling_decorator
def fill_fin_type(state: ChatState) -> ChatState:
    """
    사용자에게 graph flow 중간에 피드백을 입력 받음

    :param state: Description
    :type state: ChatState
    :return: Description
    :rtype: ChatState
    """

    human_text = interrupt("예금, 적금, 전세대출 중에 어느 상품에 관심이 있으신가요?")
    return {"query": human_text, "need_user_feedback": False}

@timing_decorator
def fill_calculator_data(state: ChatState) -> ChatState:
    """
    calculator에 필요한 데이터 입력

    :param state: Description
    :type state: ChatState
    :return: Description
    :rtype: ChatState
    """

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
        calculator_data = {key: None for key in state["calculator_columns"]}

    return {"calculator_data": calculator_data, "need_user_feedback": True}

@timing_decorator
def user_feedback(state: ChatState) -> ChatState:
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
        if key in ["최고한도", "적립유형명", "저축금리유형명"]:
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

    else:
        if category == "fixed_deposit":
            loop_or_not_method = "calc_fixed_deposit"
            return {
                "loop_or_not_method": loop_or_not_method,
            }
        elif category == "installment_deposit":
            loop_or_not_method = "calc_installment_deposit"
            return {
                "loop_or_not_method": loop_or_not_method,
            }
        elif category == "jeonse_loan":
            loop_or_not_method = "calc_jeonse_loan"
            return {
                "loop_or_not_method": loop_or_not_method,
            }


def loop_or_not_method_router(
    state: ChatState,
) -> Literal["get_user_data", "calc_fixed_deposit", "calc_installment_deposit", "calc_jeonse_loan"]:
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
def get_user_data(state: ChatState) -> ChatState:
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

    # 논리 오류. json output을 강제 했기 때문에 사용자가 입력을 하지 않아도
    # 강제된 입력 형식을 맞춰서 채워넣었을 가능성이 있음.
    # 추후 확인 해봐야함.
    return {
        "calculator_data": answer,
    }


@timing_decorator
def calc_fixed_deposit(state: ChatState) -> ChatState:
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
def calc_installment_deposit(state: ChatState) -> ChatState:
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
def calc_jeonse_loan(state: ChatState) -> ChatState:
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
def after_calculate(state: ChatState) -> ChatState:
    """

    return : dict,
    """

    return {
        "answer": state["calculated_data"],
    }
