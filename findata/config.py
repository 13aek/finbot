"""
금융상품한눈에(Open API) 데이터 수집 설정 파일
-> API 호출 시 사용되는 주요 코드와 데이터 필드를 정의합니다.

구성
1. fin_grp_dict : 금융기관 그룹 코드 (topFinGrpNo)
2. item_dict    : API 응답 필드명을 사람이 이해하기 쉬운 한글 키로 변환하는 매핑

사용처
- call_findata_api.py 내 fetch_findata() 함수에서 import되어 사용됩니다.
- 향후 다른 금융상품(적금, 대출 등) 추가 시 이 파일에 항목을 확장합니다.
"""

fin_grp_dict = {
    "020000": "은행",
    "030200": "여신전문",
    "030300": "저축은행",
    "050000": "보험회사",
    "060000": "금융투자",
}

item_dict = {
    "kor_co_nm": "금융회사명",
    "fin_co_no": "금융회사코드",
    "fin_prdt_nm": "금융상품명",
    "fin_prdt_cd": "금융상품코드",
    "join_way": "가입방법",
    "mtrt_int": "만기후이자율",
    "spcl_cnd": "우대조건",
    "join_deny": "가입제한",
    "join_member": "가입대상",
    "max_limit": "최고한도",
    "intr_rate_type": "적립유형명",
    "intr_rate_type_nm": "저축금리유형명",
    "save_trm": "저축개월",
    "intr_rate": "저축금리",
    "intr_rate2": "최고우대금리",
    "dcls_strt_day": "공시시작일",
    "dcls_end_day": "공시종료일",
    "dcls_month": "공시제출월",
}
