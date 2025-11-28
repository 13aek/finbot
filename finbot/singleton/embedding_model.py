from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embed_model():
    """
    Embedding Model Singleton instance 생성

    parameter () : None
    return BGEM3FlagModel : BGEM3FlagModel Embedding Model 객체
    """
    print("Singleton Embedding Model을 생성합니다....")
    return SentenceTransformer("BM-K/KoSimCSE-roberta-multitask")


embed_model = get_embed_model()
