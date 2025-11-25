from functools import lru_cache


@lru_cache(maxsize=1)
def get_ready_search(category="deposit"):
    db_collection_name = "finance_products" + "_" + category
    db_path = glob(os.getcwd() + "/**/qdrant_localdb", recursive=True)[0]

    client = get_qdrant_local(collection_name=db_collection_name, vector_size=1024, path=db_path)
    return model, client
