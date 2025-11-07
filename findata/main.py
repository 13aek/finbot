"""
금융상품 데이터 수집 및 저장 메인 실행 파일
- '금융상품한눈에' 오픈 API로부터 데이터를 수집(fetch)하고, 수집된 데이터를 MySQL DB에 저장(save)하는 전체 프로세스를 실행

실행 순서
1. call_findata_api.py 의 fetch_findata() 함수를 통해 금융상품 데이터 수집
2. save_to_db.py 의 save_fin_products() 함수를 통해 DB 저장
3. 실행 결과 및 오류는 콘솔에 출력됨

실행 명령어
python -m findata.main
"""

from findata.call_findata_api import fetch_findata  # API 호출 모듈
from findata.save_to_db import save_fin_products  # DB 저장 모듈

if __name__ == "__main__":
    print("금융상품 API 데이터 수집 및 저장을 시작합니다.")
    try:
        data = fetch_findata()  # 금융상품 데이터 수집
        if data:
            save_fin_products(data)  # 수집된 데이터를 DB에 저장
            print("전체 프로세스 완료.")
        else:
            print("수집된 데이터가 없습니다. API 응답을 확인하세요.")
    except Exception as e:
        print("실행 중 오류 발생:", e)
