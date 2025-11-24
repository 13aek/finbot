"""
금융상품 데이터 수집 및 저장 메인 실행 파일
- '금융상품한눈에' 오픈 API로부터 데이터를 수집(fetch)하고,
    수집된 데이터를 MySQL DB에 저장(save)하는 전체 프로세스를 실행

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

from findata.call_findata_api import fetch_findata
from findata.save_to_db import save_fin_products

FIN_CATEGORIES = [
    ("fixed_deposit", "정기예금"),
    ("installment_deposit", "적금"),
    ("jeonse_loan", "전세자금대출"),
]


if __name__ == "__main__":
    print("=== 금융상품 전체 데이터 수집 및 저장 프로세스 시작 ===")

    for key, label in FIN_CATEGORIES:
        print(f"\n>>> [{key}] {label} 데이터 수집 시작")

        try:
            data = fetch_findata(category=key)  # 금융상품 데이터 수집

            # 각 상품에 category 키 추가
            for d in data:
                d["category"] = key

            if data:
                print(f"[{key}] {len(data)}건 수집 → DB 저장")
                save_fin_products(data)
                print(f"[{key}] 저장 완료")
            else:
                print(f"[{key}] 데이터 없음")

        except Exception as e:
            print(f"[오류] {key} 처리 중 오류:", e)

    print("\n=== 전체 금융상품 수집/저장 프로세스 완료 ===")
