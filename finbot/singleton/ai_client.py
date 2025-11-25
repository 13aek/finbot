import os
import sys
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI


sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

load_dotenv("../.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@lru_cache(maxsize=1)
def get_ai_client():
    """
    AI Client Singleton instance 생성

    parameter () : None
    return OpenAI : OpenAI 객체
    """
    print("Singleton AI Client를 생성합니다....")
    return OpenAI(api_key=OPENAI_API_KEY)


ai_client = get_ai_client()
