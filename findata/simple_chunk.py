from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def make_embedding_ready_text_deposit(product: dict) -> str:
    """
    JSON 데이터 -> 자연어 문장으로 변환하는 함수
    arguments : (Dict) 금융 데이터 한건 json
    return : (str) json을 자연어로 풀어쓴 string
    """

    text = f"{product['금융회사명']}의 {product['금융상품명']}은 {product['가입대상']}이 가입할 수 있습니다. "
    # 가입 제한 (1: 제한없음, 2: 서민전용, 3: 일부 제한)
    if "가입제한" in product:
        if product["가입제한"] == "1":
            text += "가입 제한은 없으며 누구나 가입할 수 있습니다. "
        elif product["가입제한"] == "2":
            text += "이 상품은 서민전용 상품으로 가입이 제한됩니다. "
        elif product["가입제한"] == "3":
            text += "일부 고객에게 가입이 제한되는 상품입니다. "
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


def make_embedding_ready_text_installment(product: dict) -> str:
    """
    JSON 데이터 -> 자연어 문장으로 변환하는 함수 (정기적금 전용, key는 한국어)
    arguments : (Dict) 금융 데이터 한 건의 json
    return : (str) json을 자연어로 풀어쓴 string
    """

    text = (
        f"{product['금융회사명']}의 {product['금융상품명']}은 "
        f"{product['가입대상']}이 가입할 수 있는 적금 상품입니다. "
        f"가입 방법은 {product['가입방법']}으로 가능합니다. "
        f"우대조건은 {product['우대조건']}입니다. "
    )

    # 가입 제한 (1: 제한없음, 2: 서민전용, 3: 일부 제한)
    if "가입제한" in product:
        if product["가입제한"] == "1":
            text += "가입 제한은 없으며 누구나 가입할 수 있습니다. "
        elif product["가입제한"] == "2":
            text += "이 상품은 서민전용 상품으로 가입이 제한됩니다. "
        elif product["가입제한"] == "3":
            text += "일부 고객에게 가입이 제한되는 상품입니다. "

    # 최고 한도
    if product.get("최고한도"):
        text += f"최고 가입 한도는 {product['최고한도']}입니다. "

    # 적립유형명
    if product.get("적립유형명"):
        text += f"적립 유형은 {product['적립유형명']}입니다. "

    # 만기 후 이자율
    text += f"만기 후 이자율은 {product['만기후이자율']}입니다. "

    # 옵션 (저축기간 및 금리)
    if "옵션" in product and product["옵션"]:
        rate_info = ", ".join(
            [
                f"{opt['저축개월']}개월 저축 시 금리는 {opt['저축금리유형명']} 기준 {opt['저축금리']}%이며 "
                f"최고 우대금리는 {opt['최고우대금리']}%입니다"
                for opt in product["옵션"]
            ]
        )
        text += f"저축기간 및 금리 조건은 {rate_info}. "

    return text


def make_embedding_ready_text_jeonse_loan(product: dict) -> str:
    """
    JSON 데이터 -> 자연어 문장으로 변환하는 함수 (전세자금대출 전용)
    arguments : (Dict) 금융 데이터 한 건 json (key는 한국어)
    return : (str) json을 자연어로 풀어쓴 string
    """

    text = (
        f"{product['금융회사명']}의 {product['금융상품명']}은 전세자금대출 상품입니다. "
        f"가입(신청) 방법은 {product['가입방법']}입니다. "
    )

    # 대출 한도
    if product.get("대출한도"):
        text += f"대출 한도는 {product['대출한도']}입니다. "

    # 대출 상환 유형
    if product.get("대출상환유형"):
        text += f"상환 방식은 {product['대출상환유형']}입니다. "

    # 대출 금리 (최저·최고·평균)
    if product.get("최저금리") or product.get("최고금리") or product.get("평균금리"):
        rate_text = []
        if product.get("대출금리유형"):
            rate_text.append(f"금리 유형은 {product['대출금리유형']}")
        if product.get("대출금리최저"):
            rate_text.append(f"최저금리는 {product['대출금리최저']}%")
        if product.get("대출금리최고"):
            rate_text.append(f"최고금리는 {product['대출금리최고']}%")
        if product.get("전월평균금리"):
            rate_text.append(f"전월 취급 평균 금리는 {product['전월평균금리']}%")
        text += ", ".join(rate_text) + "입니다. "

    # 대출 부대 비용
    if product.get("대출부대비용"):
        text += f"대출 부대 비용은 {product['대출부대비용']}입니다. "

    # 중도상환수수료
    if product.get("중도상환수수료"):
        text += f"중도상환수수료는 {product['중도상환수수료']}입니다. "

    # 연체이자율
    if product.get("연체이자율"):
        text += f"연체 시 적용되는 이자율은 {product['연체이자율']}입니다. "

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

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=250, chunk_overlap=30
    )  # , separators=["\n\n", ",", ".", " "])
    docs = []
    for json_product in json_data_list:
        if json_product["상품카테고리"] == "정기예금":
            text = make_embedding_ready_text_deposit(json_product)
        elif json_product["상품카테고리"] == "적금":
            text = make_embedding_ready_text_installment(json_product)
        elif json_product["상품카테고리"] == "전세자금대출":
            text = make_embedding_ready_text_jeonse_loan(json_product)
        base_doc = Document(page_content=text, metadata=json_product)
        # chunk 분리
        chunks = splitter.split_documents([base_doc])
        docs.extend(chunks)

    print(f"Chunked Documents: {len(docs)}개 생성 완료\n")
    print("Chunked Documents sample : ", docs[0])
    return docs
