# rag_engine/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from openai import OpenAI

client = OpenAI()


class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self):
        self.state = {"query": "", "history": [], "answer": ""}

    def ask(self, query: str):
        self.state["query"] = query
        self.state = app_graph.invoke(self.state)
        return self.state["answer"]


class ChatState(TypedDict):
    """
    graph를 구성할 State
    """

    query: str
    history: List[Dict[str, str]]  # user & assistant message 쌍
    answer: str


# --- 노드 정의 ---


def add_to_history(state: ChatState) -> ChatState:
    """
    이전 대화 기록을 유지하면서 새 user message 추가
    """
    history = state.get("history", [])
    history.append({"role": "user", "content": state["query"]})
    return state | {"history": history}


def synthesize(state: ChatState) -> ChatState:
    """
    대화 히스토리를 프롬프트에 포함해 답변 생성
    """
    messages = [{"role": "system", "content": "너는 금융상품 추천 챗봇이야."}]
    messages.extend(state["history"])  # 이전 turn들 포함

    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

    answer = completion.choices[0].message.content
    # 히스토리에 assistant 응답 추가
    new_history = state["history"] + [{"role": "assistant", "content": answer}]
    return state | {"answer": answer, "history": new_history}


# --- 그래프 구성 ---

graph = StateGraph(ChatState)
graph.add_node("add_to_history", add_to_history)
graph.add_node("synthesize", synthesize)

graph.set_entry_point("add_to_history")
graph.add_edge("add_to_history", "synthesize")
graph.add_edge("synthesize", END)

# --- “상태 누적형” 인스턴스 생성 ---
app_graph = graph.compile()
