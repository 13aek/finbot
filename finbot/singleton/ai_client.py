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
    return OpenAI(api_key=OPENAI_API_KEY)
