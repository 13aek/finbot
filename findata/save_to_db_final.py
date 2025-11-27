import os
from pathlib import Path

import MySQLdb

from findata.config_manager import JsonConfigManager


BASE_DIR = Path(__file__).resolve().parent.parent
conf_path = BASE_DIR / "findata/config.json"
conf = JsonConfigManager(path=conf_path).values


# DB 연결
def get_conn():
    return MySQLdb.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        passwd=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        charset="utf8mb4",
    )


# 공통 필드 / 옵션 필드 정의
COMMON_BASE_FIELDS = {
    "kor_co_nm",
    "fin_co_no",
    "fin_prdt_nm",
    "fin_prdt_cd",
    "join_way",
    "dcls_strt_day",
    "dcls_end_day",
    "dcls_month",
}

OPTION_KEEP = {
    "fixed_deposit": {
        "join_member",
        "mtrt_int",
        "spcl_cnd",
        "join_deny",
        "max_limit",
        "intr_rate_type_nm",
        "save_trm",
        "intr_rate",
        "intr_rate2",
        "dcls_month",
    },
    "installment_deposit": {
        "join_member",
        "mtrt_int",
        "spcl_cnd",
        "join_deny",
        "max_limit",
        "rsrv_type_nm",
        "intr_rate_type_nm",
        "save_trm",
        "intr_rate",
        "intr_rate2",
        "dcls_month",
    },
    "jeonse_loan": {
        "loan_inci_expn",
        "erly_rpay_fee",
        "dly_rate",
        "loan_lmt",
        "rpay_type_nm",
        "lend_rate_type_nm",
        "lend_rate_min",
        "lend_rate_max",
        "lend_rate_avg",
        "dcls_month",
    },
}


# 기본 상품 저장
def save_fin_product(cur, p: dict, category_en: str, eng_to_han: dict):
    """
    fin_products
    - 3카테고리에 공통으로 존재하는 필드만 저장
    - company_type, category, description 은 별도 추가
    """
    cols = []
    vals = []

    # 공통 필드만 저장
    for eng_key in COMMON_BASE_FIELDS:
        han_key = eng_to_han.get(eng_key)
        if not han_key:
            continue
        cols.append(eng_key)
        vals.append(p.get(han_key))

    # 메타 필드
    cols.append("company_type")
    vals.append(p.get("회사유형"))

    cols.append("category")
    vals.append(category_en)

    cols.append("description")
    vals.append(p.get("상품설명"))

    placeholders = ",".join(["%s"] * len(vals))

    query = f"""
        INSERT INTO fin_products ({",".join(cols)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
            {",".join([f"{c}=VALUES({c})" for c in cols])}
    """

    cur.execute(query, vals)


# 옵션 저장 (카테고리별)
def insert_option(cur, category_en: str, fin_prdt_cd: str, p: dict, opt: dict, eng_to_han: dict):
    """
    옵션 테이블 3종
    - table: fixed_deposit_option / installment_deposit_option / jeonse_loan_option
    - OPTION_KEEP[category_en] 에 정의된 필드를
      (opt 에 있으면 opt에서, 없으면 p에서) 가져와 1 row로 저장
    """
    table = f"{category_en}_option"

    # 새 ID 생성
    cur.execute(f"SELECT IFNULL(MAX(id), 0) + 1 FROM {table}")
    new_id = cur.fetchone()[0]

    cols = ["id", "fin_prdt_cd"]
    vals = [new_id, fin_prdt_cd]

    allowed_fields = OPTION_KEEP[category_en]

    for eng_key in allowed_fields:
        han_key = eng_to_han.get(eng_key)
        if not han_key:
            # config에 정의 안된 필드면 스킵
            continue

        # 옵션(dict opt)에 우선권, 없으면 baseList(dict p)에서
        value = opt.get(han_key, p.get(han_key))

        cols.append(eng_key)
        vals.append(value)

    placeholders = ",".join(["%s"] * len(vals))

    query = f"""
        INSERT INTO {table} ({",".join(cols)})
        VALUES ({placeholders})
    """

    cur.execute(query, vals)


# 전체 저장
def save_to_db_final(data: list[dict]):
    conn = get_conn()
    cur = conn.cursor()

    print(f"save_to_db.py {len(data)}건 저장 시작")

    for p in data:
        category_kor = p["상품카테고리"]  # 정기예금 / 적금 / 전세자금대출
        category_en = conf.category[category_kor]  # fixed_deposit / installment_deposit / jeonse_loan

        fin_prdt_cd = p["금융상품코드"]

        # config.json: eng → han 매핑
        eng_to_han = conf.tags[category_en]

        # fin_products 저장
        save_fin_product(cur, p, category_en, eng_to_han)

        # 옵션 저장
        for opt in p.get("옵션", []):
            insert_option(cur, category_en, fin_prdt_cd, p, opt, eng_to_han)

    conn.commit()
    cur.close()
    conn.close()

    print("DB 저장 완료")
