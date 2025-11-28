from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore


@lru_cache(maxsize=1)
def get_checkpoint():
    """
    Embedding Model Singleton instance 생성

    parameter () : None
    return MemorySaver, InMemoryStore : 휘발성 memory 객체 생성
    """
    print("Chatting Checkpoint를 생성합니다....")
    return MemorySaver(), InMemoryStore()


memory, memory_store = get_checkpoint()
