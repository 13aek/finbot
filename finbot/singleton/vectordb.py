import os
from functools import lru_cache
from glob import glob

from findata.vector_db import get_qdrant_local


@lru_cache(maxsize=1)
def get_qdrant_client(category="deposit"):
    db_collection_name = "finance_products" + "_" + category
    db_path = glob(os.getcwd() + "/**/qdrant_localdb", recursive=True)[0]
    print("Singleton Qdrant Client를 생성합니다....")
    return get_qdrant_local(collection_name=db_collection_name, vector_size=1024, path=db_path)


qdrant_client = get_qdrant_client()
