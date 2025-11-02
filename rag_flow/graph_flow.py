# rag_engine/graph.py
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any
from typing import Annotated
from typing import Literal
from functools import partial
from openai import OpenAI
import pandas as pd
from sqlalchemy import create_engine


client = OpenAI()

class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self):
        self.state = {"query": "", "history": [], "answer": ""}
        """
        DB에서 history 들고와서 저장
        """

    def ask(self, query: str):
        self.state["query"] = query
        self.state = app_graph.invoke(self.state)
        return self.state["answer"]
    
    
def keep_last_n(existing: List[Dict], new: List[Dict], n: int = 10) -> List[Dict]:
    """
    최근 n개 항목만 유지하는 리듀서
    """
    combined = (existing or []) + (new or [])
    return combined[-n:]  # 마지막 n개만 반환

keep_last_10 = partial(keep_last_n, n=10)


class ChatState(TypedDict):
    """
    graph를 구성할 State
    """
    
    mode: str # chat mode : first conversation & first meet, first conversation & Nth meet, Nth conversation
    search_method: str # search method : DB search, RAG search
    query: str
    history: Annotated[List[Dict[str, str]], keep_last_10]  # user & assistant message 쌍
    answer: str


# 노드 정의

def conditional_about_history(state: ChatState) -> Dict:
    """
    history에 따라 분기 발생 
    """
    # 복합 조건 평가
    if not state["history"]:
        mode = "First_hello"
    elif state["history"]:
        if state["history"][-1].get("new",False):
            mode = "Normal_chat"
        elif state["history"][0].get("old",False):
            mode = "Nth_hello"
        else:
            print('Mode를 찾을 수 없습니다.')
    else:
        print('Mode를 찾을 수 없습니다.')

    return {
        "mode": mode,
    }

def mode_router(state: ChatState) -> Literal["First_hello", "Nth_hello", "Normal_chat"]:
    """
    Mode에 따라 라우팅
    """
    return state["mode"]


def first_conversation(state: ChatState) -> ChatState:
    """
    이전 history 아예 없이 첫 방문 첫 인사
    """
    
    hello = "안녕하세요. 첫 방문이시군요! 무엇을 도와드릴까요?"
    history = {"role": "assistant", "content": hello, "state": "new"}
    
    return {"history": history}

def nth_conversation(state: ChatState) -> ChatState:
    """
    이전 history 존재. 첫 인사.
    history 요약해서 
    """
    histories = state["history"]
    questions = [ history["content"] for history in histories if history["role"] == "user"]
    
    messages = [{"role": "system", "content": "너는 몇 개의 문장을 3단어로 요약해야해."}]
    messages.append({"role": "user", "content": questions})  # 이전 질문들 모두 

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    summary = completion.choices[0].message.content
    
    hello = f"안녕하세요. 지난번에는 {summary}에 대해 물어보셨군요! 오늘은 무엇을 도와드릴까요?"
    history = {"role": "assistant", "content": hello, "state": "new"}
    
    return {"history": history}

def conditional_about_query(state: ChatState) -> Dict:
    """
    query에 따라 분기 발생 
    """
    # 복합 조건 평가
    query = state["query"]
    if "검색" in query:
        method = "DB_search"
    else:
        method = "RAG_search"
    return {
        "search_method": method,
    }

def method_router(state: ChatState) -> Literal["DB_search", "RAG_search"]:
    """
    Search Method에 따라 라우팅
    """
    return state["search_method"]

def add_to_history(state: ChatState) -> ChatState:
    """
    이전 대화 기록을 유지하면서 새 user message 추가
    """
    history = state.get("history", [])
    history.append({"role": "user", "content": state["query"], "state": "new"})
    return {"history": history}


def DB_search(state: ChatState) -> ChatState:
    """
    대화 히스토리를 프롬프트에 포함해 답변 생성
    """
    messages = [{"role": "system", "content": ""}]

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    answer = completion.choices[0].message.content
    # 히스토리에 assistant 응답 추가
    new_history = state["history"] + [{"role": "assistant", "content": answer, "state": "new"}]
    return state | {"answer": answer, "history": new_history}

def RAG_search(state: ChatState) -> ChatState:
    """
    대화 히스토리를 프롬프트에 포함해 답변 생성
    """
    messages = [{"role": "system", "content": ""}]

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    answer = completion.choices[0].message.content
    # 히스토리에 assistant 응답 추가
    new_history = state["history"] + [{"role": "assistant", "content": answer, "state": "new"}]
    return state | {"answer": answer, "history": new_history}




# Node 정의

graph = StateGraph(ChatState)
graph.add_node("conditional_about_history", conditional_about_history)
graph.add_node("First_hello", first_conversation)
graph.add_node("Nth_hello", first_conversation)
graph.add_node("Normal_chat", first_conversation)
graph.add_node("add_to_history", add_to_history)
graph.add_node("conditional_about_query", conditional_about_query)
graph.add_node("DB_search", DB_search)
graph.add_node("RAG_search", RAG_search)


# Graph flow 구성

graph.add_edge(START, "conditional_about_history")
graph.add_conditional_edges(
    "conditional_about_history",
    mode_router,
    {
        "First_hello": "First_hello",
        "Nth_hello": "Nth_hello",
        "Normal_chat": "Normal_chat"
    }
)

graph.add_edge("First_hello", END)
graph.add_edge("Nth_hello", END)
graph.add_edge("Normal_chat", "add_to_history")
graph.add_edge("add_to_history", "conditional_about_query")
graph.add_conditional_edges(
    "conditional_about_query",
    method_router,
    {
        "DB_search": "DB_search",
        "RAG_search": "RAG_search",
    }
)
graph.add_edge("DB_search", END)
graph.add_edge("RAG_search", END)

# 인스턴스 생성
app_graph = graph.compile()
