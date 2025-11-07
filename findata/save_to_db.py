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
from typing import Dict, List  # 타입 힌팅용 라이브러리

import MySQLdb  # DB 저장 시 사용
from dotenv import load_dotenv  # 환경 변수 로드를 위한 라이브러리
from sqlalchemy import create_engine  # MySQL 연결을 위한 SQLAlchemy 엔진

# 환경 변수 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# 금융상품 데이터를 MySQL에 저장하는 함수
def save_fin_products(data: List[Dict]) -> None:
    """
    금융상품 데이터를 MySQL DB에 저장합니다.
    :param data: fetch_findata()에서 반환된 List[Dict] 형식의 금융상품 데이터
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
            company_name VARCHAR(100),
            product_name VARCHAR(200),
            product_code VARCHAR(50),
            maturity_interest TEXT,
            conditions TEXT,
            join_method VARCHAR(255),
            join_target VARCHAR(255),
            max_limit VARCHAR(255),
            disclosure_start VARCHAR(20),
            disclosure_end VARCHAR(20),
            disclosure_month VARCHAR(10)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 데이터 삽입 쿼리
    insert_query = """
        INSERT INTO fin_products (
            company_type, company_name, product_name, product_code,
            maturity_interest, conditions, join_method, join_target,
            max_limit, disclosure_start, disclosure_end, disclosure_month
        ) VALUES (
            %(회사유형)s, %(금융회사명)s, %(금융상품명)s, %(금융상품코드)s,
            %(만기후이자율)s, %(우대조건)s, %(가입방법)s, %(가입대상)s,
            %(최고한도)s, %(공시시작일)s, %(공시종료일)s, %(공시제출월)s
        )
    """

    # 데이터 삽입
    inserted = 0
    for item in data:
        try:
            cursor.execute(insert_query, item)
            inserted += 1
        except Exception as e:
            print("Insert Error:", e)  # 오류 발생 시 출력
            continue  # 다음 데이터로 진행

    conn.commit()
    print(f"MySQL에 {inserted}건 저장 완료")

    # 연결 종료
    cursor.close()
    conn.close()
