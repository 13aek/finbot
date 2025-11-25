import os
import uuid
from glob import glob

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

from findata.call_findata_api import fetch_findata
from findata.simple_chunk import chunk


# ===============================
# 🚫 기존 QdrantLocal 기반 코드 제거
# ===============================

def get_qdrant_server(collection_name: str, vector_size: int = 1024) -> QdrantClient:
    """
    Qdrant 서버 모드로 접속하는 함수
    - collection이 없으면 자동 생성
    - QDRANT_URL 환경변수 기반 (docker-compose 또는 .env)
    """

    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    client = QdrantClient(url=qdrant_url)

    # 존재하지 않을 경우 컬렉션 생성
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )

    return client


# ===============================
# 🟢 서버 기반 VectorDB 저장 함수
# ===============================

def save_vector_db(
    chunked_docs: list[str],
    collection_name: str = "finance_products",
    category: str = "deposit",
    vector_size: int = 1024,
):
    """
    VectorDB에 Chunked data 저장하는 함수 (Qdrant 서버 기반)
    - BGE-m3 임베딩
    - Qdrant 서버에 직접 업로드
    """

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
    db_collection_name = f"{collection_name}_{category}"

    client = get_qdrant_server(
        collection_name=db_collection_name,
        vector_size=vector_size,
    )

    points = []
    for i, doc in enumerate(tqdm(chunked_docs, desc="임베딩 + 업로드 중")):
        vec = model.encode([doc.page_content], return_dense=True)["dense_vecs"][0]
        point_id = str(uuid.uuid4())
        payload = {**doc.metadata, "chunk_id": i, "text": doc.page_content}
        points.append(PointStruct(id=point_id, vector=vec, payload=payload))

    client.upsert(collection_name=db_collection_name, points=points)

    print(f"\n 업로드 완료: 총 {len(points)}개 chunk (Document 기반)")
    return client


# ===============================
# 🟦 검색에 사용되는 Ready 함수
# ===============================

def get_ready_search(category="deposit"):
    """
    임베딩 모델 로드 + Qdrant 서버 접속 반환
    """

    # 컬렉션 이름 구성
    db_collection_name = f"finance_products_{category}"

    # 모델 로드
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)

    # Qdrant 서버 접속
    client = get_qdrant_server(
        collection_name=db_collection_name,
        vector_size=1024,
    )

    return model, client


# ===============================
# 🧪 테스트용 스크립트
# ===============================

if __name__ == "__main__":
    save_vector_db(chunk(fetch_findata()))
