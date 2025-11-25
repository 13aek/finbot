from functools import lru_cache

from FlagEmbedding import BGEM3FlagModel


@lru_cache(maxsize=1)
def get_embed_model():
    print("Singleton Embedding Model을 생성합니다....")
    return BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)


embed_model = get_embed_model()
