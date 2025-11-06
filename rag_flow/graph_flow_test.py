from graph_flow import ChatSession

session = ChatSession()


def scenario1():  # first_hello
    visited = session.state["visited"]
    query = None
    answer = session.ask(query, visited)
    return answer


def scenario2():  # Nth_hello
    # history 존재
    session.state["history"].append(
        {"role": "user", "content": "저녁 뭐먹을까", "state": "old"}
    )
    session.state["visited"] = True

    visited = session.state["visited"]
    query = None
    answer = session.ask(query, visited)
    return answer


print("시나리오1 : ", scenario1())
print("시나리오2 : ", scenario2())
