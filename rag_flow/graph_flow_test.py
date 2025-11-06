from graph_flow import ChatSession

session = ChatSession()


def view():
    visited = session.state["visited"]
    print(visited)
    if not visited:
        answer = session.ask("", visited)
    else:
        pass
        # query = "예금 3프로 이상인거 알려줘"
        # answer = session.ask(query)
    print(answer)


view()
