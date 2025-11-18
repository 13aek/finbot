import argparse
import os  # 운영 체제와 상호작용하기 위한 라이브러리
from datetime import date, datetime
from pathlib import Path  # 파일 경로 처리를 위한 라이브러리
from pprint import pprint

import requests
from dotenv import load_dotenv

from findata.config_manager import JsonConfigManager


"""
<금융상품한눈에 api 데이터 처리 가이드>

- 개발 화면에서 조회조건에 맞는 총 상품 수 확인은 조회결과 데이터 중 'total_count'값을 참조합니다.
- 개발 화면에서 페이징 처리 시 전체 페이지 수 처리는 조회결과 데이터 중 'max_page_no'값을 참조합니다.
- 개발 화면에서 페이징 처리 시 현재 페이지 표시는 조회결과 데이터 중 'now_page_no'값을 참조합니다.
- 페이징 처리 예시는 상단의 관련소스에서 'goPage'함수와 49~59Line을 참조합니다.
"""

# .env 파일을 읽어 환경 변수로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # 프로젝트 폴더의 .env.example에 환경변수 입력
conf_path = BASE_DIR / "findata/config.json"
# config load
conf = JsonConfigManager(path=conf_path).values

# dotenv를 활용하여 API 키 가져오기
FINAPI_KEY = os.getenv("FINAPI_KEY")


# 금융 데이터를 가져오는 함수 정의
def fetch_findata(category="fixed_deposit") -> list[dict]:
    """
    정기예금, 적금, 전세자금대출 호출 가능하도록 develop한 version
    # 데이터베이스에 저장
    return : List[Dict(상품)], 데이터 리스트 반환
    """
    # category 유효성
    assert category in ["fixed_deposit", "installment_deposit", "jeonse_loan"]
    # 현재 날짜 저장
    today = date.today()
    format_today = today.strftime("%Y%m%d")
    today_date = datetime(int(format_today[:4]), int(format_today[4:6]), int(format_today[6:8]))

    # API 호출에 필요한 파라미터(필수)
    url = conf.urls[category]
    fin_grp_dict = conf.fin_co_no
    item_dict = conf.tags[category]

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

        assert ex_data["result"]["err_msg"] == "정상"
        assert ex_data["result"]["total_count"] >= 0
        assert ex_data["result"]["max_page_no"] >= 0
        code_dict.setdefault(group, {})
        code_dict[group]["total_count"] = ex_data["result"]["total_count"]
        code_dict[group]["max_page_no"] = ex_data["result"]["max_page_no"]

    # 모든 데이터 조회 및 정리"fixed_deposit", "installment_deposit", "jeonse_loan"
    fin_cat = {
        "fixed_deposit": "정기예금",
        "installment_deposit": "적금",
        "jeonse_loan": "전세자금대출",
    }

    print("금융상품 통합비교공시 '금융상품한눈에' 오픈 API 호출을 시작합니다.")
    print(f"Current Finance Category : {fin_cat[category]}")
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
                        rep_data[item_dict[api_key]] = tmp_data["result"]["baseList"][i][api_key]
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
                                rep_data_in[item_dict[api_key2]] = tmp_data["result"]["optionList"][
                                    j
                                ][api_key2]

                        rep_data["옵션"].append(rep_data_in)
                data.append(rep_data)
    print(f"{len(data)} 건 자료 처리완료.")
    print("*" * 30, "예시", "*" * 30)
    pprint(data[0])
    print("*" * 63)

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This is calling finance data program from api")
    # ["fixed_deposit", "installment_deposit", "jeonse_loan"] 중 하나
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default="fixed_deposit",
        help="category of finance data",
    )
    args = parser.parse_args()
    fetch_findata(category=args.category)
