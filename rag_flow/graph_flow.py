# rag_engine/graph.py
import os
import sys
from functools import lru_cache, partial
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel
from langgraph.graph import END, START, StateGraph
from openai import OpenAI


sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from qdrant_client import QdrantClient

from findata.vector_db import get_ready_search


@lru_cache(maxsize=1)
def load_model_and_db():
    """
    인자에 대한 반환값을 기억하여
    해당 함수가 동일한 리턴값을 반환한다면
    함수를 새로 실행시키는 것이 아닌 기억하고 있는 반환값을 그대로 사용합니다.
    """
    return get_ready_search()


@lru_cache(maxsize=1)
def load_chat_client(api_key: str):
    """
    인자에 대한 반환값을 기억하여
    해당 함수가 동일한 리턴값을 반환한다면
    함수를 새로 실행시키는 것이 아닌 기억하고 있는 반환값을 그대로 사용합니다.
    """
    return OpenAI(api_key=api_key)


# 환경변수 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

load_dotenv("../.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

load_model_and_db()
client = load_chat_client(OPENAI_API_KEY)


class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self, user_history):
        self.state = {"visited": False, "history": []}
        self.state["embed_model"], self.state["vector_db"] = load_model_and_db()

        """
        DB에서 history 들고와서 저장해야함. 
        각 history는 Dict 하나로 저장.
        DB에 있던 것은 오래된 것이므로 각 history에 'state' key 추가. value 'old'로 지정
        """
        # 히스토리가 DB에 있다면 old history로 추가
        if user_history:
            self.state["history"].append({"role": "user", "content": user_history, "state": "old"})
            self.state["visited"] = True
        # DB에 history 있으면 True
        # self.state["history"].append(
        #     {"role": "user", "content": "저녁 뭐먹을까", "state": "old"}
        # )
        # self.state["visited"] = True

    def ask(self, query: str):
        """
        사용자의 질문을 받고 Langgraph를 거쳐 답변을 생성

        Args:
            query (str): 사용자의 질문 query
            visited (bool): 사용자 방문여부(history유무)
        Returns:
            answer (str): Langgraph state의 answer
        """
        self.state["recommend_mode"] = False

        # history 유무에 따라 분기
        if not self.state["history"]:
            visited = False
            self.state["visited"] = False
        else:
            visited = True
            self.state["visited"] = True

        if not visited:
            self.state = app_graph.invoke(self.state)
        else:
            self.state["query"] = query
            self.state = app_graph.invoke(self.state)
        return self.state["answer"]


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


keep_last_10 = partial(keep_last_n, n=10)


class ChatState(TypedDict):
    """
    graph를 구성할 State Class
    """

    embed_model: BGEM3FlagModel
    vector_db: QdrantClient

    visited: bool
    # chat mode :
    #   (First_hello)first conversation & first meet,
    #   (Nth_hello)first conversation & Nth meet,
    #   (Normal_chat)Nth conversation
    mode: str
    # agent method : ("rag_search", "calculator", "finword_explain", "normal_chat")
    agent_method: str
    recommend_mode: bool
    query: str  # user query
    history: Annotated[list[dict[str, str]], keep_last_10]  # user, assistant message 쌍
    answer: str  # LLM answer


# 노드 정의


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


def first_conversation(state: ChatState) -> ChatState:
    """
    이전 history 아예 없이 첫 방문 첫 인사

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 history dict.
    """

    answer = "안녕하세요. 첫 방문이시군요! 무엇을 도와드릴까요?"

    return {"answer": answer}


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

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    summary = completion.choices[0].message.content

    answer = f"안녕하세요. 지난번에는 {summary} 등 에 대해 물어보셨군요! 오늘은 무엇을 도와드릴까요?"

    return {"answer": answer}


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

    completion = client.chat.completions.create(
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
) -> Literal["recommend_mode", "calculate_mode", "explain_mode", "normal_mode"]:  # "db_search",
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

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=400,
    )

    answer = completion.choices[0].message.content
    return {"answer": answer}


def rag_search(state: ChatState) -> ChatState:
    """
    사용자의 query와 유사한 RAG 결과를 생성하고, RAG 결과를 바탕으로 답변 반환

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 answer를 반환
    """
    embed_model = state["embed_model"]
    vector_db = state["vector_db"]
    topk = 3
    user_query = state["query"]
    q_vec = embed_model.encode([user_query], return_dense=True)["dense_vecs"][0]
    hits = vector_db.search(collection_name="finance_products_deposit", query_vector=q_vec, limit=topk)

    vector_db_answer = hits[0].payload

    messages = [
        {
            "role": "system",
            "content": "너는 금융 도메인 전문가이자 고객 상담 AI야. vector_db에서 제공된 정보를 근거로만 답변해야 해.",
        },
        {
            "role": "user",
            "content": f"다음은 vector_db에서 찾은 정보야:\n{vector_db_answer}",
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n이 'vector_db에서 찾은 정보'만 참고해서 사용자의 질문에 정확히 답변해줘.",
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=600,
        # tools=
    )
    answer = completion.choices[0].message.content
    recommend_mode = True
    return {"answer": answer, "recommend_mode": recommend_mode}


def calculator(state: ChatState) -> ChatState:
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
            "content": "너는 금융 도메인 전문가이자 계산 전문가야.",
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n을 계산해줘.",
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=600,
        # tools=
    )
    answer = completion.choices[0].message.content

    return {"answer": answer}


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
            "content": "너는 금융 도메인 전문가이자 고객 상담 AI야. user의 질문에 답해줘.",
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n 에 맞는 설명을 해줘.",
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=600,
        # tools=
    )
    answer = completion.choices[0].message.content

    return {"answer": answer}


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
            "content": "너는 금융 도메인 전문가이자 고객 상담 AI야. 질문에 상담사처럼 상담해줘.",
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n에 답해줘.",
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=600,
        # tools=
    )
    answer = completion.choices[0].message.content

    return {"answer": answer}


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
    return {"history": new_history, "visited": True}


# Node 정의

graph = StateGraph(ChatState)
graph.add_node("conditional_about_history", conditional_about_history)
graph.add_node("first_hello", first_conversation)
graph.add_node("Nth_hello", nth_conversation)

graph.add_node("conditional_about_query", conditional_about_query)
graph.add_node("rag_search", rag_search)
graph.add_node("calculator", calculator)
graph.add_node("fin_word_explain", fin_word_explain)
graph.add_node("normal_chat", normal_chat)
graph.add_node("add_to_history", add_to_history)


# Graph flow 구성

graph.add_edge(START, "conditional_about_history")
graph.add_conditional_edges(
    "conditional_about_history",
    mode_router,
    {
        "first_hello": "first_hello",
        "Nth_hello": "Nth_hello",
        "agent_mode": "conditional_about_query",
    },
)
graph.add_edge("first_hello", "add_to_history")
graph.add_edge("Nth_hello", "add_to_history")
graph.add_conditional_edges(
    "conditional_about_query",
    agent_method_router,
    {
        "recommend_mode": "rag_search",
        "calculate_mode": "calculator",
        "explain_mode": "fin_word_explain",
        "normal_mode": "normal_chat",
    },
)
graph.add_edge("rag_search", "add_to_history")
graph.add_edge("calculator", "add_to_history")
graph.add_edge("fin_word_explain", "add_to_history")
graph.add_edge("normal_chat", "add_to_history")
graph.add_edge("add_to_history", END)

# 인스턴스 생성
app_graph = graph.compile()
