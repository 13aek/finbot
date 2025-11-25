from functools import lru_cache

from FlagEmbedding import BGEM3FlagModel


@lru_cache(maxsize=1)
def get_embed_model():
    return BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
