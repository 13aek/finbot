import os  # 운영 체제와 상호작용하기 위한 라이브러리
from datetime import date, datetime
from pathlib import Path  # 파일 경로 처리를 위한 라이브러리
from pprint import pprint
from typing import Dict, List

import requests  # HTTP 요청을 보내기 위한 라이브러리
from dotenv import load_dotenv  # 환경 변수 로드를 위한 라이브러리

"""
<금융상품한눈에 api 데이터 처리 가이드>

- 개발 화면에서 조회조건에 맞는 총 상품 수 확인은 조회결과 데이터 중 'total_count'값을 참조합니다.
- 개발 화면에서 페이징 처리 시 전체 페이지 수 처리는 조회결과 데이터 중 'max_page_no'값을 참조합니다.
- 개발 화면에서 페이징 처리 시 현재 페이지 표시는 조회결과 데이터 중 'now_page_no'값을 참조합니다.
- 페이징 처리 예시는 상단의 관련소스에서 'goPage'함수와 49~59Line을 참조합니다.
"""

# API 호출에 필요한 파라미터(필수)
# 금융기관별 코드 list: 데이터 명세 참고
fin_grp_dict = {
    "020000": "은행",  # 은행
    "030200": "여신전문",  # 여신전문
    "030300": "저축은행",  # 저축은행
    "050000": "보험회사",  # 보험회사
    "060000": "금융투자",  # 금융투자
}

# 수집할 상품 스펙의 태그명 list: 데이터 명세 참고
item_dict = {
    "kor_co_nm": "금융회사명",  # 금융회사명
    "fin_co_no": "금융회사코드",  # 금융회사코드
    "fin_prdt_nm": "금융상품명",  # 금융상품명
    "fin_prdt_cd": "금융상품코드",  # 금융상품코드
    "join_way": "가입방법",  # 가입방법
    "mtrt_int": "만기후이자율",  # 만기후이자율
    "spcl_cnd": "우대조건",  # 우대조건
    "join_deny": "가입제한",  # 가입제한 1:제한X, 2:서민전용, 3:일부제한
    "join_member": "가입대상",  # 가입대상
    "max_limit": "최고한도",  # 최고한도
    "intr_rate_type": "적립유형명",  # 적립유형명
    "intr_rate_type_nm": "저축금리유형명",  # 저축금리유형명
    "save_trm": "저축개월",  # 저축개월 [단위: 개월]
    "intr_rate": "저축금리",  # 저축금리 [소수점 2자리]
    "intr_rate2": "최고우대금리",  # 최고우대금리
    "dcls_strt_day": "공시시작일",  # 공시시작일
    "dcls_end_day": "공시종료일",  # 공시종료일
    "dcls_month": "공시제출월",  # 공시제출월
}

load_dotenv()  # .env 파일을 읽어 환경 변수로 설정합니다.

# dotenv를 활용하여 API 키 가져오기
FINAPI_KEY = os.getenv("FINAPI_KEY")
# 공식 문서를 참고하여 API 검색 URL 설정하기
FIXED_DEPOSIT_URL = os.getenv("FIXED_DEPOSIT_URL")


# 금융 데이터를 가져오는 함수 정의
def fetch_findata() -> List[Dict]:
    """
    일단은 예금만 가져오게 설정. 적금, 연금저축, 주택담보대출, 전세자금대출, 개인신용대출을 불러오려면 develop 필요.

    return : List[Dict(상품)]
    """
    # 현재 날짜 저장
    today = date.today()
    format_today = today.strftime("%Y%m%d")
    today_date = datetime(
        int(format_today[:4]), int(format_today[4:6]), int(format_today[6:8])
    )
    # URL 저장
    url = FIXED_DEPOSIT_URL
    # 최종 데이터 저장 할 data
    data = []
    # 금융기관별 api info 가져오기
    code_dict = {}
    for group in fin_grp_dict.keys():

        ex_params = {
            "auth": FINAPI_KEY,  # API 키
            "topFinGrpNo": group,  #  금융회사가 속한 권역 코드
            "pageNo": 2,  # 페이지 번호
        }

        # [ requests 문서를 참고하여 HTTP GET 요청 보내는 코드 작성하기 ]
        ex_response = requests.get(url, params=ex_params)  # .json()
        ex_data = ex_response.json()
        # print(group, ex_data["result"]["total_count"])
        assert ex_data["result"]["err_msg"] == "정상"
        assert ex_data["result"]["total_count"] >= 0
        assert ex_data["result"]["max_page_no"] >= 0
        code_dict.setdefault(group, {})
        code_dict[group]["total_count"] = ex_data["result"]["total_count"]
        code_dict[group]["max_page_no"] = ex_data["result"]["max_page_no"]
    # 모든 데이터 조회 및 정리
    # [ requests 문서를 참고하여 응답 데이터를  python의 dict 타입으로 변환하여 data 변수에 저장 ]
    print("금융상품 통합비교공시 '금융상품한눈에' 오픈 API 호출을 시작합니다.")
    for group in fin_grp_dict.keys():
        group_name = fin_grp_dict[group]
        count = code_dict[group]["total_count"]
        print(f"{group_name} 자료를 {count}건 불러옵니다.")

        for page_no in range(1, code_dict[group]["max_page_no"] + 1):
            params = {
                "auth": FINAPI_KEY,  # API 키
                "topFinGrpNo": group,  #  금융회사가 속한 권역 코드
                "pageNo": page_no,  # 페이지 번호
            }
            response = requests.get(url, params=params)
            tmp_data = response.json()

            for i in range(len(tmp_data["result"]["baseList"])):
                # 현재 판매 중인 금융상품인지 확인(공시종료가 안되었는지)
                end_day = tmp_data["result"]["baseList"][i]["dcls_end_day"]
                if end_day is None:
                    pass
                elif isinstance(end_day, str):
                    end_date = datetime(
                        int(end_day[:4]),
                        int(end_day[4:6]),
                        int(end_day[6:8]),
                    )
                    data_diff = end_date - today_date
                    if data_diff.days > 0:
                        pass
                    else:
                        continue

                # key 이름 변경을 위한 복제 데이터
                rep_data = {"회사유형": fin_grp_dict[group]}

                for api_key in tmp_data["result"]["baseList"][i].keys():
                    if api_key in item_dict.keys():
                        rep_data[item_dict[api_key]] = tmp_data["result"]["baseList"][
                            i
                        ][api_key]
                rep_data["옵션"] = []

                for j in range(len(tmp_data["result"]["optionList"])):

                    if (
                        tmp_data["result"]["optionList"][j]["dcls_month"]
                        == tmp_data["result"]["baseList"][i]["dcls_month"]
                        and tmp_data["result"]["optionList"][j]["fin_co_no"]
                        == tmp_data["result"]["baseList"][i]["fin_co_no"]
                        and tmp_data["result"]["optionList"][j]["fin_prdt_cd"]
                        == tmp_data["result"]["baseList"][i]["fin_prdt_cd"]
                    ):
                        # key 이름 변경을 위한 복제 데이터
                        rep_data_in = {}

                        for api_key2 in tmp_data["result"]["optionList"][j].keys():
                            if api_key2 in item_dict.keys():
                                rep_data_in[item_dict[api_key2]] = tmp_data["result"][
                                    "optionList"
                                ][j][api_key2]

                        rep_data["옵션"].append(rep_data_in)
                data.append(rep_data)
    print(f"{len(data)} 건 자료 처리완료.")
    print("*" * 30, "예시", "*" * 30)
    pprint(data[0])
    print("*" * 63)
    return data
