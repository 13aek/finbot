from langgraph.graph import END, START, StateGraph

from rag_flow.graph_nodes import (
    ChatState,
    add_to_history,
    agent_method_router,
    calculator,
    conditional_about_history,
    conditional_about_query,
    fin_word_explain,
    first_conversation,
    mode_router,
    normal_chat,
    nth_conversation,
    rag_search,
)


class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self, user_history):
        self.state = {"visited": False, "history": []}

        """
        DB에서 history 들고와서 저장해야함. 
        각 history는 Dict 하나로 저장.
        DB에 있던 것은 오래된 것이므로 각 history에 'state' key 추가. value 'old'로 지정
        """
        # 히스토리가 DB에 있다면 old history로 추가
        if user_history:
            self.state["history"].append({"role": "user", "content": user_history, "state": "old"})
            self.state["visited"] = True

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
