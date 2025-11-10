# rag_engine/graph.py
import os
import sys
from functools import partial
from typing import Annotated, Any, Dict, List, Literal, TypedDict

import pandas as pd
from django.contrib.auth import get_user_model
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import OpenAI
from sqlalchemy import create_engine

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient

from findata.vectorDB import get_ready_search

load_dotenv("../.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self, user_history):
        self.state = {"visited": False, "history": []}
        self.state["embed_model"], self.state["vectorDB"] = get_ready_search()

        """
        DB에서 history 들고와서 저장해야함. 
        각 history는 Dict 하나로 저장.
        DB에 있던 것은 오래된 것이므로 각 history에 'state' key 추가. value 'old'로 지정
        """
        # 히스토리가 DB에 있다면 old history로 추가
        if user_history:
            self.state["history"].append(
                {"role": "user", "content": user_history, "state": "old"}
            )
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


def keep_last_n(existing: List[Dict], new: List[Dict], n: int = 10) -> List[Dict]:
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
    vectorDB: QdrantClient

    visited: bool
    mode: str  # chat mode : (First_hello)first conversation & first meet, (Nth_hello)first conversation & Nth meet, (Normal_chat)Nth conversation
    search_method: str  # search method : DB search, RAG search
    query: str  # user query
    history: Annotated[List[Dict[str, str]], keep_last_10]  # user, assistant message 쌍
    answer: str  # LLM answer


# 노드 정의


def conditional_about_history(state: ChatState) -> Dict:
    """
    history에 따라 분기 발생

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 mode dict, mode = ("first_hello", "Nth_hello", "normal_chat")
    """
    # 복합 조건 평가
    if not state["visited"]:
        mode = "first_hello"

    elif state["visited"]:

        if state["history"][-1]["state"] == "old":
            mode = "Nth_hello"

        elif state["history"][-1]["state"] == "new":
            mode = "normal_chat"

        else:
            print("Mode를 찾을 수 없습니다.")

    else:
        print("Mode를 찾을 수 없습니다.")

    return {
        "mode": mode,
    }


def mode_router(state: ChatState) -> Literal["first_hello", "Nth_hello", "normal_chat"]:
    """
    Mode에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["first_hello", "Nth_hello", "normal_chat"] 중 하나의 값으로 제한
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
    questions = [
        history["content"] for history in histories if history["role"] == "user"
    ]

    messages = [
        {
            "role": "system",
            "content": "너는 주어지는 몇 개의 문장을 '3단어'로 요약해야해.",
        }
    ]
    messages.append(
        {"role": "user", "content": f"다음은 주어진 문장들이야 :\n{questions}"}
    )  # 이전 질문들 모두
    messages.append({"role": "user", "content": "주어진 문장들을 3단어로 요약해줘."})

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    summary = completion.choices[0].message.content

    answer = f"안녕하세요. 지난번에는 {summary} 등 에 대해 물어보셨군요! 오늘은 무엇을 도와드릴까요?"

    return {"answer": answer}


def conditional_about_query(state: ChatState) -> Dict:
    """
    query에 따라 분기 발생.(하려했으나 DB search는 다른 함수로 빠졌기 때문에 RAG search만 존재)

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 method dict, method = ("RAG_search") # DB_search
    """
    # 복합 조건 평가
    # query = state["query"]
    # if "검색" in query:
    #     method = "DB_search"
    # else:
    method = "RAG_search"
    return {
        "search_method": method,
    }


def method_router(state: ChatState) -> Literal["RAG_search"]:  # "DB_search",
    """
    Search Method에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["RAG_search"] 중 하나의 값으로 제한
    """
    return state["search_method"]


def DB_search(state: ChatState) -> ChatState:
    """
    대화 히스토리를 프롬프트에 포함해 답변 생성

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 answer를 반환
    """
    DB_answer = "DB 검색 결과"
    user_query = state["query"]
    messages = [
        {
            "role": "system",
            "content": "너는 금융 도메인 전문가이자 고객 상담 AI야. DB에서 제공된 정보를 근거로만 답변해야 해.",
        },
        {"role": "user", "content": f"다음은 DB에서 찾은 정보야:\n{DB_answer}"},
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


def RAG_search(state: ChatState) -> ChatState:
    """
    사용자의 query와 유사한 RAG 결과를 생성하고, RAG 결과를 바탕으로 답변 반환

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 answer를 반환
    """
    embed_model = state["embed_model"]
    vectorDB = state["vectorDB"]
    topk = 3
    user_query = state["query"]
    q_vec = embed_model.encode([user_query], return_dense=True)["dense_vecs"][0]
    hits = vectorDB.search(
        collection_name="finance_products_deposit", query_vector=q_vec, limit=topk
    )

    VectorDB_answer = hits[0].payload

    messages = [
        {
            "role": "system",
            "content": "너는 금융 도메인 전문가이자 고객 상담 AI야. VectorDB에서 제공된 정보를 근거로만 답변해야 해.",
        },
        {
            "role": "user",
            "content": f"다음은 VectorDB에서 찾은 정보야:\n{VectorDB_answer}",
        },
        {
            "role": "user",
            "content": f"질문: {user_query}\n이 'VectorDB에서 찾은 정보'만 참고해서 사용자의 질문에 정확히 답변해줘.",
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
        new_history.append(
            {"role": "assistant", "content": state["answer"], "state": "new"}
        )
    else:
        new_history.append(
            {"role": "assistant", "content": state["answer"], "state": "new"}
        )
    return {"history": new_history, "visited": True}


# Node 정의

graph = StateGraph(ChatState)
graph.add_node("conditional_about_history", conditional_about_history)
graph.add_node("first_hello", first_conversation)
graph.add_node("Nth_hello", nth_conversation)
graph.add_node("normal_chat", first_conversation)
graph.add_node("add_to_history", add_to_history)
graph.add_node("RAG_search", RAG_search)


# Graph flow 구성

graph.add_edge(START, "conditional_about_history")
graph.add_conditional_edges(
    "conditional_about_history",
    mode_router,
    {
        "first_hello": "first_hello",
        "Nth_hello": "Nth_hello",
        "normal_chat": "normal_chat",
    },
)

graph.add_edge("first_hello", "add_to_history")
graph.add_edge("Nth_hello", "add_to_history")
graph.add_edge("normal_chat", "RAG_search")
graph.add_edge("RAG_search", "add_to_history")
graph.add_edge("add_to_history", END)

# 인스턴스 생성
app_graph = graph.compile()
