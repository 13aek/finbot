from findata.call_findata_api import create_description, fetch_findata
from findata.save_to_db_final import save_to_db_final

if __name__ == "__main__":
    print("=== RAW 금융상품 + 설명 생성 후 저장 시작 ===")
    data = fetch_findata("fixed_deposit")
    data += fetch_findata("installment_deposit")
    data += fetch_findata("jeonse_loan")

    # 여기서 LLM으로 상품설명 생성
    data = create_description(data)

    print(f"총 {len(data)}건 통합 데이터 반환 완료")
    print(f"main.py {len(data)}건 저장 시작")

    save_to_db_final(data)

    print("=== 완료 ===")
