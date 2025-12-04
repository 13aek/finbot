from functools import lru_cache
from pathlib import Path

from findata.vector_db import get_qdrant_local, get_qdrant_server


BASE_DIR = Path(__file__).resolve().parent.parent.parent
vectordb_path = BASE_DIR / "findata" / "qdrant_localdb"
print(vectordb_path)


@lru_cache(maxsize=1)
def get_qdrant_client(category="all", save_to="server"):
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
    if save_to == "server":
        qdrant_client = get_qdrant_server(collection_name=db_collection_name)
    elif save_to == "local":
        qdrant_client = get_qdrant_local(collection_name=collection_name, category=category, path=vectordb_path)
    print(f"Singleton Qdrant Client를 생성했습니다 (Qdrant {save_to} 모드).")
    return qdrant_client


# 앱 전역에서 사용할 싱글톤 QdrantClient
# qdrant_client = get_qdrant_client(save_to="server")
qdrant_client = None