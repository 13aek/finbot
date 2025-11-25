from functools import lru_cache
from findata.vector_db import get_ready_search


@lru_cache(maxsize=1)
def get_qdrant_client(category="deposit"):
    """
    Qdrant 서버용 Singleton Client 생성
    - get_ready_search()는 (model, client)을 반환하므로
      여기서는 client만 반환하면 된다.
    """
    _, qdrant_client = get_ready_search(category=category)
    print("Singleton Qdrant Client를 생성했습니다 (Qdrant 서버 모드).")
    return qdrant_client


# 앱 전역에서 사용할 싱글톤 QdrantClient
qdrant_client = get_qdrant_client()
