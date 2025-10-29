from typing import Dict, List
from call_findata_api import fetch_findata
from pprint import pprint
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


def make_embedding_ready_text_deposit(product: Dict) -> str:
    """
    JSON 데이터 -> 자연어 문장으로 변환하는 함수
    """

    text = f"{product['금융회사명']}의 {product['금융상품명']}은 {product['가입대상']}이 가입할 수 있습니다. "
    text += f"가입 방법은 {product['가입방법']}으로 가능합니다. 우대조건은 {product['우대조건']}입니다. "
    text += f"만기 후 이자율은 {product['만기후이자율']}입니다. "
    if "옵션" in product and product["옵션"]:
        rate_info = ", ".join(
            [
                f"{opt['저축개월']}개월 저축할 때에 저축금리는 {opt['저축금리유형명']}으로 {opt['저축금리']}% 이며 최고 우대 금리는 {opt['최고우대금리']}"
                for opt in product["옵션"]
            ]
        )
        text += f"저축기간 및 금리는 {rate_info} 입니다."
    return text


def make_embedding_ready_sentence_deposit(data_list: List[Dict]) -> List[str]:
    """
    JSON 데이터 -> 문장을 리스트로 반환하는 함수
    아마 안 쓸 것 같음
    """

    return [make_embedding_ready_text_deposit(data) for data in data_list]
