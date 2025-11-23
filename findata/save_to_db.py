"""
금융상품 데이터 저장 모듈 (save_to_db.py)
- API를 통해 수집된 금융상품 데이터를 MySQL DB에 저장하는 모듈입니다.

주요 기능
1. MySQL 연결 (환경 변수 기반)
2. fin_products 테이블 자동 생성 (없을 시 생성)
3. 데이터 삽입 (중복 방지 X, 단순 insert)
4. 에러 발생 시 출력 후 다음 데이터로 continue
"""

import os  # 운영체제 환경 변수 접근을 위한 라이브러리
from pathlib import Path  # 파일 경로 처리를 위한 라이브러리

import MySQLdb  # DB 저장 시 사용
from dotenv import load_dotenv  # 환경 변수 로드를 위한 라이브러리

# 환경 변수 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# 금융상품 데이터를 MySQL에 저장하는 함수
def save_fin_products(data: list[dict]) -> None:
    """
    금융상품 데이터를 MySQL DB에 저장
    UNIQUE KEY(product_code, disclosure_month) 기준으로
    기존 데이터가 있으면 UPDATE, 없으면 INSERT
    """

    # MySQL 연결 시작
    conn = MySQLdb.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        passwd=DB_PASSWORD,
        db=DB_NAME,
        charset="utf8mb4",
        autocommit=True,
    )
    cursor = conn.cursor()

    # fin_products 테이블 생성 (없을 시 생성)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_type VARCHAR(50),
            category VARCHAR(50),
            company_name VARCHAR(100),
            product_name VARCHAR(200),
            product_code VARCHAR(50),
            maturity_interest LONGTEXT,
            conditions LONGTEXT,
            join_method VARCHAR(255),
            join_target VARCHAR(255),
            max_limit VARCHAR(255),
            disclosure_start VARCHAR(20),
            disclosure_end VARCHAR(20),
            disclosure_month VARCHAR(10),
            UNIQUE KEY unique_product_month (product_code, disclosure_month)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # INSERT + UPDATE
    insert_query = """
        INSERT IGNORE INTO fin_products (
            category, company_type, company_name, product_name, product_code,
            join_method, join_target, max_limit,
            maturity_interest, conditions,
            disclosure_start, disclosure_end, disclosure_month
        ) VALUES (
            %(category)s, %(회사유형)s, %(금융회사명)s, %(금융상품명)s, %(금융상품코드)s,
            %(가입방법)s, %(가입대상)s, %(최고한도)s,
            %(만기후이자율)s, %(우대조건)s,
            %(공시시작일)s, %(공시종료일)s, %(공시제출월)s
        )
        ON DUPLICATE KEY UPDATE
            company_type = VALUES(company_type),
            company_name = VALUES(company_name),
            product_name = VALUES(product_name),
            join_method = VALUES(join_method),
            join_target = VALUES(join_target),
            max_limit = VALUES(max_limit),
            maturity_interest = VALUES(maturity_interest),
            conditions = VALUES(conditions),
            disclosure_start = VALUES(disclosure_start),
            disclosure_end = VALUES(disclosure_end)
    """

    # 데이터 삽입
    inserted = 0
    updated = 0

    for idx, item in enumerate(data, start=1):
        # None / 누락 값 방지
        safe_item = {
            "category": item.get("category", "") or "",
            "회사유형": item.get("회사유형", "") or "",
            "금융회사명": item.get("금융회사명", "") or "",
            "금융상품명": item.get("금융상품명", "") or "",
            "금융상품코드": item.get("금융상품코드", "") or "",
            "만기후이자율": item.get("만기후이자율", "") or "",
            "우대조건": item.get("우대조건", "") or "",
            "가입방법": item.get("가입방법", "") or "",
            "가입대상": item.get("가입대상", "") or "",
            "최고한도": item.get("최고한도", "") or "",
            "공시시작일": item.get("공시시작일", "") or "",
            "공시종료일": item.get("공시종료일", "") or "",
            "공시제출월": item.get("공시제출월", "") or "",
        }

        cursor.execute(insert_query, safe_item)

        # rowcount 동작 설명:
        # INSERT 실행 시:
        #   - 신규 INSERT → rowcount == 1
        #   - ON DUPLICATE KEY UPDATE 발생 → rowcount == 2
        #       (MySQL의 ON DUPLICATE KEY UPDATE 특성: UPDATE가 발생하면 2로 반환)

        if cursor.rowcount == 1:
            inserted += 1  # 신규 저장
        elif cursor.rowcount == 2:
            updated += 1  # 기존 데이터 업데이트

    conn.commit()
    print(f"MySQL INSERT: {inserted}건 / UPDATE: {updated}건")

    cursor.close()
    conn.close()
