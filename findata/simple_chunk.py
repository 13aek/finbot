
from pprint import pprint

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


<<<<<<< HEAD

=======
>>>>>>> b6f750a38a5ee4da794440afd7ce6f7b515b91f1
def make_embedding_ready_text_deposit(product: dict) -> str:
    """
    JSON 데이터 -> 자연어 문장으로 변환하는 함수
    arguments : (Dict) 금융 데이터 한건 json
    return : (str) json을 자연어로 풀어쓴 string
    """

    text = f"{product['금융회사명']}의 {product['금융상품명']}은 {product['가입대상']}이 가입할 수 있습니다. "
    text += f"가입 방법은 {product['가입방법']}으로 가능합니다. 우대조건은 {product['우대조건']}입니다. "
    text += f"만기 후 이자율은 {product['만기후이자율']}입니다. "
    if "옵션" in product and product["옵션"]:
        rate_info = ", ".join(
            [
                f"{opt['저축개월']}개월 저축할 때에 저축금리는 {opt['저축금리유형명']}으로 \
                    {opt['저축금리']}% 이며 최고 우대 금리는 {opt['최고우대금리']}"
                for opt in product["옵션"]
            ]
        )
        text += f"저축기간 및 금리는 {rate_info} 입니다."
    return text


def make_embedding_ready_sentence_deposit(data_list: list[dict]) -> list[str]:
    """
    JSON 데이터 -> 문장을 리스트로 반환하는 함수
    (아마 안 쓸 것 같음)
    arguments : (List[Dict]) 금융 데이터 json List[Dict]
    return : (List[str]) json을 자연어로 풀어 쓴 List[str]
    """

    return [make_embedding_ready_text_deposit(data) for data in data_list]


def chunk(json_data_list: list[dict]) -> list[str]:
    """
    모든 금융데이터 List[Dict]를 chunk하는 함수
    후에 조정 필요
    arguments : (List[Dict]) 모든 금융 데이터 json List[Dict]
    return : (List[str]) 모든 금융 데이터의 chunk data List
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=150, chunk_overlap=30, separators=["\n\n", ",", ".", " "])
    docs = []
    for json_product in json_data_list:
        text = make_embedding_ready_text_deposit(json_product)
        base_doc = Document(page_content=text, metadata=json_product)
        # chunk 분리
        chunks = splitter.split_documents([base_doc])
        docs.extend(chunks)

    print(f"Chunked Documents: {len(docs)}개 생성 완료\n")
    pprint("Chunked Documents sample : ", docs[0])
    return docs
