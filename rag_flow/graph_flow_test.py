from rag_flow.graph_flow import ChatSession
history = "저녁 뭐먹을까"
session = ChatSession(history)


def scenario1():  # first_hello
    query = None
    answer = session.ask(query)
    return answer


def scenario2():  # Nth_hello
    # history 존재
    session.state["history"].append(
        {"role": "user", "content": "저녁 뭐먹을까", "state": "old"}
    )
    session.state["visited"] = True

    query = None
    answer = session.ask(query)
    return answer

def scenario3():  # RAG_Search
    # history 존재
    # 대화 중
    session.state["history"].append(
        {"role": "user", "content": "저녁 뭐먹을까", "state": "old"}       
    )
    session.state["history"].append(
        {"role": "user", "content": "안녕 나는 강태인. 자치회듀오 중 반장을 맡고 있지. 후후", "state": "new"}      
    )
     
    session.state["visited"] = True

    queries = ["직업이 없어도 가입할 수 있는 예금이 있나~?",
             "우리은행 상품 중에 금리 높은거 추천해줘",
             "제일 오래 저축할 수 있는 상품은 뭐야"]
    answers = []
    for query in queries:
        answer = session.ask(query)
        answers.append(answer)
    return queries, answers


print("시나리오1 : ", scenario1())
print("시나리오2 : ", scenario2())
print('-'*50)
print('시나리오3')
queries, answers = scenario3()
for (q, a) in zip(queries, answers):
    print('-'*50)
    print("질문 : ", q)
    print("답변 : ", a)
print('-'*50)
