from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from finbot.singleton.chat_checkpoint import memory, memory_store
from rag_flow.graph_nodes import (
    ChatState,
    add_to_history,
    after_calculate,
    agent_method_router,
    before_calculate,
    calc_fixed_deposit,
    calc_installment_deposit,
    calc_jeonse_loan,
    calculator_method_router,
    check_findata,
    classify_feedback,
    conditional_about_history,
    conditional_about_query,
    conditional_about_recommend,
    feedback_router,
    fill_calculator_data,
    fin_word_explain,
    first_conversation,
    get_user_data,
    human_feedback,
    loop_or_not_method_router,
    mode_router,
    normal_chat,
    nth_conversation,
    rag_search,
    recommend_method_router,
    user_feedback,
    using_only_user_input_data,
    feedback_or_not_method_router,
    fill_fin_type,

)


class ChatSession:
    """
    Chat Session을 만들 클래스
    대화 History 저장 용도
    """

    def __init__(self, user_history):
        self.state = {"visited": False, "history": []}
        self.state["need_user_feedback"] = False
        """
        DB에서 history 들고와서 저장해야함. 
        각 history는 Dict 하나로 저장.
        DB에 있던 것은 오래된 것이므로 각 history에 'state' key 추가. value 'old'로 지정
        """
        # 히스토리가 DB에 있다면 old history로 추가
        if user_history:
            self.state["history"].append({"role": "user", "content": user_history, "state": "old"})
            self.state["visited"] = True

    def ask(self, query: str, thread: dict, need_user_feedback: bool = False):
        """
        사용자의 질문을 받고 Langgraph를 거쳐 답변을 생성

        Args:
            query (str): 사용자의 질문 query
            thread (dict): 영속성을 위한 사용자 정보, 채팅룸 정보
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
            self.state = app_graph.invoke(self.state, thread)
        else:
            if not need_user_feedback:
                self.state["query"] = query
                self.state = app_graph.invoke(self.state, thread)
            else:
                self.state["query"] = query
                self.state = app_graph.invoke(Command(resume=query, update=self.state), thread)
        return self.state


# Node 정의

graph = StateGraph(ChatState)
graph.add_node("conditional_about_history", conditional_about_history)
graph.add_node("first_hello", first_conversation)
graph.add_node("Nth_hello", nth_conversation)

graph.add_node("conditional_about_query", conditional_about_query)
graph.add_node("conditional_about_recommend", conditional_about_recommend)
graph.add_node("rag_search", rag_search)
graph.add_node("human_feedback", human_feedback)
graph.add_node("classify_feedback", classify_feedback)
graph.add_node("before_calculate", before_calculate)

graph.add_node("check_findata", check_findata)
graph.add_node("fill_calculator_data", fill_calculator_data)
graph.add_node("using_only_user_input_data", using_only_user_input_data)
graph.add_node("fill_fin_type", fill_fin_type)

graph.add_node("user_feedback", user_feedback)
graph.add_node("get_user_data", get_user_data)
graph.add_node("calc_fixed_deposit", calc_fixed_deposit)
graph.add_node("calc_installment_deposit", calc_installment_deposit)
graph.add_node("calc_jeonse_loan", calc_jeonse_loan)
graph.add_node("after_calculate", after_calculate)


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
        "recommend_mode": "conditional_about_recommend",
        "calculate_mode": "before_calculate",
        "explain_mode": "fin_word_explain",
        "normal_mode": "normal_chat",
    },
)
graph.add_conditional_edges(
    "conditional_about_recommend",
    recommend_method_router,
    {
        "fixed_deposit": "rag_search",
        "installment_deposit": "rag_search",
        "jeonse_loan": "rag_search",
        "all": "rag_search",
    },
)
graph.add_edge("rag_search", "human_feedback")
graph.add_edge("human_feedback", "classify_feedback")
graph.add_conditional_edges(
    "classify_feedback",
    feedback_router,
    {
        "yes": "before_calculate",
        "no": "conditional_about_query",
    },
)
graph.add_edge("before_calculate", "check_findata")
graph.add_conditional_edges(
    "check_findata",
    calculator_method_router,
    {
        "using_recommended_data": "fill_calculator_data",
        "using_only_user_input_data": "using_only_user_input_data",
    },
)

graph.add_conditional_edges(
    "using_only_user_input_data",
    feedback_or_not_method_router,
    {
        "pass": "user_feedback",
        "fill_fin_type": "fill_fin_type",
    },
)
graph.add_edge("fill_fin_type", "using_only_user_input_data")

graph.add_edge("fill_calculator_data", "user_feedback")
graph.add_conditional_edges(
    "user_feedback",
    loop_or_not_method_router,
    {
        "get_user_data": "get_user_data",
        "calc_fixed_deposit": "calc_fixed_deposit",
        "calc_installment_deposit": "calc_installment_deposit",
        "calc_jeonse_loan": "calc_jeonse_loan",
    },
)

graph.add_edge("get_user_data", "user_feedback")
graph.add_edge("calc_fixed_deposit", "after_calculate")
graph.add_edge("calc_installment_deposit", "after_calculate")
graph.add_edge("calc_jeonse_loan", "after_calculate")
graph.add_edge("after_calculate", "add_to_history")


graph.add_edge("fin_word_explain", "add_to_history")
graph.add_edge("normal_chat", "add_to_history")
graph.add_edge("add_to_history", END)

# 인스턴스 생성
app_graph = graph.compile(checkpointer=memory, store=memory_store)
