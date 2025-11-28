import time
from functools import wraps


def timing_decorator(func):
    """노드 실행 시간 측정 데코레이터"""

    @wraps(func)
    def wrapper(state):
        start_time = time.time()
        result = func(state)
        execution_time = time.time() - start_time

        # 실행 시간 추가
        if isinstance(result, dict):
            result["execution_time"] = execution_time

        print(f"{func.__name__} executed in {execution_time:.3f} seconds")
        return result

    return wrapper


def error_handling_decorator(func):
    """에러 처리 데코레이터"""

    @wraps(func)
    def wrapper(state):
        try:
            return func(state)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            return {"error": str(e), "error_node": func.__name__, "status": "failed"}

    return wrapper
