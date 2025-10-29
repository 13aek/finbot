from typing import Dict, List
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from tqdm import tqdm
import uuid


def get_qdrant_local(
    collection_name: str = "finance_products",
    category: str = "deposit",
    vector_size: int = 1024,
    path: str = "./qdrant_localdb",
) -> QdrantClient:
    """
    Qdrant VectorDB 불러오는 함수
    - 로컬 경로에 Qdrant localdb 사용
    - collection이 이미 있으면 그대로 사용
    - 없으면 create_collection 수행

    arguments:
        (str) collection_name: 금융데이터 DB 이름
        (str) category: 세부 카테고리
        (int) vector_size: embedding vector size
        (str) path: VectorDB 저장 경로
    return:
        QdrantClient: Qdrant VectorDB Client
    """
    collection_name = collection_name + "_" + category
    client = QdrantClient(path=path)

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    # 존재하면 아무 것도 하지 않고 그대로 반환
    return client
