# rag_engine/graph.py
import os
from functools import partial
from typing import Annotated, Any, Dict, List, Literal, TypedDict

import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import OpenAI
from sqlalchemy import create_engine

load_dotenv("../.env.example")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self):
        self.state = {"query": "", "history": [], "answer": ""}
        """
        DB에서 history 들고와서 저장해야함
        """

    def ask(self, query: str):
        """
        사용자의 질문을 받고 Langgraph를 거쳐 답변을 생성

        Args:
            query (str): 사용자의 질문 query
        Returns:
            answer (str): Langgraph state의 answer
        """
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
        Dict: state에 업데이트 할 mode dict, mode = ("First_hello", "Nth_hello", "Normal_chat")
    """
    # 복합 조건 평가
    if not state["history"]:
        mode = "First_hello"
    elif state["history"]:
        if state["history"][-1].get("new", False):
            mode = "Normal_chat"
        elif state["history"][0].get("old", False):
            mode = "Nth_hello"
        else:
            print("Mode를 찾을 수 없습니다.")
    else:
        print("Mode를 찾을 수 없습니다.")

    return {
        "mode": mode,
    }


def mode_router(state: ChatState) -> Literal["First_hello", "Nth_hello", "Normal_chat"]:
    """
    Mode에 따라 라우팅

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Literal: ["First_hello", "Nth_hello", "Normal_chat"] 중 하나의 값으로 제한
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

    hello = "안녕하세요. 첫 방문이시군요! 무엇을 도와드릴까요?"
    history = {"role": "assistant", "content": hello, "state": "new"}

    return {"history": history}


def nth_conversation(state: ChatState) -> ChatState:
    """
    이전 history 존재. 첫 인사.
    history 요약해서 제공

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: state에 업데이트 할 history dict.
    """
    histories = state["history"]
    questions = [
        history["content"] for history in histories if history["role"] == "user"
    ]

    messages = [
        {
            "role": "system",
            "content": "너는 주어지는 몇 개의 문장을 3단어로 요약해야해.",
        }
    ]
    messages.append({"role": "user", "content": questions})  # 이전 질문들 모두

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    summary = completion.choices[0].message.content

    hello = f"안녕하세요. 지난번에는 {summary}에 대해 물어보셨군요! 오늘은 무엇을 도와드릴까요?"
    history = {"role": "assistant", "content": hello, "state": "new"}

    return {"history": history}


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


def add_to_history(state: ChatState) -> ChatState:
    """
    이전 대화 기록을 유지하면서 새 user message 추가

    Args:
        state (TypedDict): Graph의 state
    Returns:
        history Dict: state의 history update
    """
    new_history = {"role": "user", "content": state["query"], "state": "new"}
    return {"history": new_history}


def DB_search(state: ChatState) -> ChatState:
    """
    대화 히스토리를 프롬프트에 포함해 답변 생성

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 history를 반환
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
    # 히스토리에 assistant 응답 추가
    new_history = {"role": "assistant", "content": answer, "state": "new"}
    return {"answer": answer, "history": new_history}


def RAG_search(state: ChatState) -> ChatState:
    """
    사용자의 query와 유사한 RAG 결과를 생성하고, RAG 결과를 바탕으로 답변 반환

    Args:
        state (TypedDict): Graph의 state
    Returns:
        Dict: LLM의 답변과 새로운 history를 반환
    """
    user_query = state["query"]

    VectorDB_answer = "VectorDB 검색 결과"

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
    )
    answer = completion.choices[0].message.content
    # 히스토리에 assistant 응답 추가
    new_history = {"role": "assistant", "content": answer, "state": "new"}
    return {"answer": answer, "history": new_history}


# Node 정의

graph = StateGraph(ChatState)
graph.add_node("conditional_about_history", conditional_about_history)
graph.add_node("First_hello", first_conversation)
graph.add_node("Nth_hello", first_conversation)
graph.add_node("Normal_chat", first_conversation)
graph.add_node("add_to_history", add_to_history)
# graph.add_node("conditional_about_query", conditional_about_query)
# graph.add_node("DB_search", DB_search)
graph.add_node("RAG_search", RAG_search)


# Graph flow 구성

graph.add_edge(START, "conditional_about_history")
graph.add_conditional_edges(
    "conditional_about_history",
    mode_router,
    {
        "First_hello": "First_hello",
        "Nth_hello": "Nth_hello",
        "Normal_chat": "Normal_chat",
    },
)

graph.add_edge("First_hello", END)
graph.add_edge("Nth_hello", END)
graph.add_edge("Normal_chat", "add_to_history")
graph.add_edge("add_to_history", "RAG_search")
# graph.add_edge("add_to_history", "conditional_about_query")
# graph.add_conditional_edges(
#     "conditional_about_query",
#     method_router,
#     {
#         "DB_search": "DB_search",
#         "RAG_search": "RAG_search",
#     }
# )
# graph.add_edge("DB_search", END)
graph.add_edge("RAG_search", END)

# 인스턴스 생성
app_graph = graph.compile()
