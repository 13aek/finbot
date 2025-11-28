from functools import lru_cache

from findata.vector_db import get_qdrant_server


@lru_cache(maxsize=1)
def get_qdrant_client(category="all"):
    """
    Qdrant 서버용 Singleton Client 생성
    - get_ready_search()는 (model, client)을 반환하므로
      여기서는 client만 반환하면 된다.

    Embedding Model Singleton instance 생성

    parameter (str) : category 지정
    return QdrnatClient : QdrnatClient Vector DB Client 객체
    """
    collection_name = "finance_products"
    db_collection_name = f"{collection_name}_{category}"
    qdrant_client = get_qdrant_server(collection_name=db_collection_name)
    print("Singleton Qdrant Client를 생성했습니다 (Qdrant 서버 모드).")
    return qdrant_client


# 앱 전역에서 사용할 싱글톤 QdrantClient
qdrant_client = get_qdrant_client()
