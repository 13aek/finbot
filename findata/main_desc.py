"""
금융상품 데이터 수집 및 저장 메인 실행 파일
- '금융상품한눈에' 오픈 API로부터 데이터를 수집(fetch)하고, 수집된 데이터를 MySQL DB에 저장(save)하는 전체 프로세스를 실행

실행 순서
1. call_findata_api.py 의 fetch_findata() 함수를 통해 금융상품 데이터 수집
2. save_to_db.py 의 save_fin_products() 함수를 통해 DB 저장
3. 실행 결과 및 오류는 콘솔에 출력됨

실행 명령어
python -m findata.main

모든 카테고리 저장 처리:
1) fixed_deposit (정기예금)
2) installment_deposit (적금)
3) jeonse_loan (전세대출)
"""

import pickle
from pathlib import Path

from findata.save_to_db import save_fin_products


BASE_DIR = Path(__file__).resolve().parent.parent
data_path = BASE_DIR / "findata" / "data"

if __name__ == "__main__":
    print("=== 금융상품 전체 데이터 수집 및 저장 프로세스 시작 ===")
    with open(data_path / "findata_all.pkl", "rb") as f:
        loaded_data = pickle.load(f)

    try:
        if loaded_data:
            print(f"{len(loaded_data)}건 수집 → DB 저장")
            save_fin_products(loaded_data)
            print("저장 완료")
        else:
            print("데이터 없음")

    except Exception as e:
        print("처리 중 오류:", e)

    print("\n=== 전체 금융상품 수집/저장 프로세스 완료 ===")
