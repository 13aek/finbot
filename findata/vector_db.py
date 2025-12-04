import os
import sys
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

load_dotenv("../.env")
QDRANT_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")


def get_qdrant_local(
    collection_name: str = "finance_products",
    category: str = "fixed_deposit",
    vector_size: int = 768,
    path: str = "./qdrant_localdb",
) -> QdrantClient:
    db_collection_name = collection_name + "_" + category
    client = QdrantClient(path=path)

    if not client.collection_exists(db_collection_name):
        client.create_collection(
            collection_name=db_collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    return client


def get_qdrant_server(collection_name: str, vector_size: int = 768) -> QdrantClient:
    """
    Qdrant 서버 모드로 접속하는 함수
    - collection이 없으면 자동 생성
    - QDRANT_URL 환경변수 기반 (docker-compose 또는 .env)
    """

    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    print("qdrant_url : ", qdrant_url)
    client = QdrantClient(url=qdrant_url)
    # client = QdrantClient(host="localhost", port=6333)
    # client = QdrantClient(
    #     url=QDRANT_URL,
    #     api_key=QDRANT_API_KEY,
    # )

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    return client


def save_vector_db(
    chunked_docs: list[str],
    collection_name: str = "finance_products",
    category: str = "fixed_deposit",
    vector_size: int = 768,
    path: str = "./qdrant_localdb",
    save_to: str = "local",
) -> QdrantClient:
    """
    VectorDB에 Chunked data 저장하는 함수 (Qdrant 서버 기반)
    - BGE-m3 임베딩
    - Qdrant 서버에 직접 업로드

    VectorDB에 Chunked data 저장하는 함수
    - "BAAI/bge-m3" Embedding Model 사용
    - Qdrant VectorDB 사용
    arguments:
        (List[str]) chunked_docs: Chunking된 금융데이터 리스트
        (str) collection_name: 금융데이터 DB 이름
        (str) category: 세부 카테고리
        (int) vector_size: embedding vector size
        (str) path: VectorDB 저장 경로
    return:
        QdrantClient: Qdrant VectorDB Client
    """

    # bge-m3 임베딩 모델 로드
    model = SentenceTransformer("BM-K/KoSimCSE-roberta-multitask")
    db_collection_name = f"{collection_name}_{category}"
    print(f"Qdrant Client를 {save_to}에서 불러옵니다......")
    # Qdrant 초기화
    if save_to == "local":
        client = get_qdrant_local(
            collection_name=collection_name,
            category=category,
            vector_size=vector_size,
            path=path,
        )
    elif save_to == "server":
        client = get_qdrant_server(
            collection_name=db_collection_name,
            vector_size=vector_size,
        )
    print("Qdrant Client Loaded......")
    points = []
    for i, doc in enumerate(tqdm(chunked_docs, desc="임베딩 + 업로드 중")):
        vec = model.encode([doc.page_content], convert_to_numpy=True)[0]
        point_id = str(uuid.uuid4())
        payload = {**doc.metadata, "chunk_id": i, "text": doc.page_content}
        points.append(PointStruct(id=point_id, vector=vec, payload=payload))
    batch_size = 200
    for i in range(0, len(points), batch_size):
        client.upsert(
            collection_name=db_collection_name, points=points[i : i + batch_size]
        )
    # client.upsert(collection_name=db_collection_name, points=points)

    print(f"\n 업로드 완료: 총 {len(points)}개 chunk (Document 기반)")
    return client


def get_ready_search(category="fixed_deposit", save_to="local"):
    """
    임베딩 모델 로드 + Qdrant 서버 접속 반환
    """

    model = SentenceTransformer("BM-K/KoSimCSE-roberta-multitask")
    # 컬렉션 이름 구성
    db_collection_name = f"finance_products_{category}"

    print(">>> 실행됨: get_ready_search()")
    print(">>> BGE 모델 로딩 완료")

    if save_to == "local":
        client = get_qdrant_local(
            collection_name="finance_products",
            category=category,
            vector_size=768,
        )
    elif save_to == "server":
        client = get_qdrant_server(
            collection_name=db_collection_name,
            vector_size=768,
        )

    return model, client
