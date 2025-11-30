import json
from pathlib import Path

from easydict import EasyDict


class JsonConfigManager:
    """
    Json설정파일을 관리
    """

    def __init__(self, **kwargs):  # path
        self.values = EasyDict()
        if kwargs:
            self.file_path = kwargs["path"]  # 파일경로 저장
            self.reload()

    def reload(self):
        """
        설정을 리셋하고 설정파일을 다시 로딩
        """
        self.clear()
        if self.file_path:
            with open(self.file_path, encoding="utf-8") as f:
                self.values.update(json.load(f))

    def clear(self):
        """
        설정을 리셋
        """
        self.values.clear()

    def update(self, in_dict):
        """
        기존 설정에 새로운 설정을 업데이트한다(최대 3레벨까지만)
        """
        for k1, v1 in in_dict.items():
            if isinstance(v1, dict):
                for k2, v2 in v1.items():
                    if isinstance(v2, dict):
                        for k3, v3 in v2.items():
                            self.values[k1][k2][k3] = v3
                    else:
                        self.values[k1][k2] = v2
            else:
                self.values[k1] = v1

    def save(self, save_file_name):
        """
        설정값을 json파일로 저장
        """

        if save_file_name:
            with open(save_file_name, "w", encoding="utf-8") as f:
                json.dump(dict(self.values), f, ensure_ascii=False, indent="\t")


if __name__ == "__main__":
    """
    금융상품한눈에(Open API) 데이터 수집 설정 파일
    -> API 호출 시 사용되는 주요 코드와 데이터 필드를 정의합니다.

    사용처
    - call_findata_api.py 내 fetch_findata() 함수에서 load되어 사용됩니다.
    - 향후 다른 금융상품 추가 시 항목을 확장합니다.
    """

    BASE_DIR = Path(__file__).resolve().parent.parent
    save_path = BASE_DIR / "findata" / "config.json"

    jm = JsonConfigManager()
    jm.values.category = {
        "정기예금": "fixed_deposit",
        "적금": "installment_deposit",
        "전세대출": "jeonse_loan",
    }
    jm.values.urls = {
        "fixed_deposit": "http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json?",
        "installment_deposit": "http://finlife.fss.or.kr/finlifeapi/savingProductsSearch.json?",
        "jeonse_loan": "http://finlife.fss.or.kr/finlifeapi/rentHouseLoanProductsSearch.json?",
    }

    jm.values.fin_co_no = {
        "020000": "은행",  # 은행
        "030200": "여신전문",  # 여신전문
        "030300": "저축은행",  # 저축은행
        "050000": "보험회사",  # 보험회사
        "060000": "금융투자",  # 금융투자
    }
    jm.values.tags = {}
    jm.values.tags.fixed_deposit = {
        "kor_co_nm": "금융회사명",  # 금융회사명
        "fin_co_no": "금융회사코드",  # 금융회사코드
        "fin_prdt_nm": "금융상품명",  # 금융상품명
        "fin_prdt_cd": "금융상품코드",  # 금융상품코드
        "join_member": "가입대상",  # 가입대상
        "join_way": "가입방법",  # 가입방법
        "mtrt_int": "만기후이자율",  # 만기후이자율
        "spcl_cnd": "우대조건",  # 우대조건
        "join_deny": "가입제한",  # 가입제한 1:제한X, 2:서민전용, 3:일부제한
        "max_limit": "최고한도",  # 최고한도
        "intr_rate_type_nm": "저축금리유형명",  # 저축금리유형명
        "save_trm": "저축개월",  # 저축개월 [단위: 개월]
        "intr_rate": "저축금리",  # 저축금리 [소수점 2자리]
        "intr_rate2": "최고우대금리",  # 최고우대금리
        "dcls_strt_day": "공시시작일",  # 공시시작일
        "dcls_end_day": "공시종료일",  # 공시종료일
        "dcls_month": "공시제출월",  # 공시제출월
    }

    jm.values.tags.installment_deposit = {
        "kor_co_nm": "금융회사명",  # 금융회사명
        "fin_co_no": "금융회사코드",  # 금융회사코드
        "fin_prdt_nm": "금융상품명",  # 금융상품명
        "fin_prdt_cd": "금융상품코드",  # 금융상품코드
        "join_member": "가입대상",  # 가입대상
        "join_way": "가입방법",  # 가입방법
        "mtrt_int": "만기후이자율",  # 만기후이자율
        "spcl_cnd": "우대조건",  # 우대조건
        "join_deny": "가입제한",  # 가입제한 1:제한X, 2:서민전용, 3:일부제한
        "max_limit": "최고한도",  # 최고한도
        "rsrv_type_nm": "적립유형명",  # 적립유형명
        "intr_rate_type_nm": "저축금리유형명",  # 저축금리유형명
        "save_trm": "저축개월",  # 저축개월 [단위: 개월]
        "intr_rate": "저축금리",  # 저축금리 [소수점 2자리]
        "intr_rate2": "최고우대금리",  # 최고우대금리
        "dcls_strt_day": "공시시작일",  # 공시시작일
        "dcls_end_day": "공시종료일",  # 공시종료일
        "dcls_month": "공시제출월",  # 공시제출월
    }

    jm.values.tags.jeonse_loan = {
        "kor_co_nm": "금융회사명",  # 금융회사명d
        "fin_co_no": "금융회사코드",  # 금융회사코드d
        "fin_prdt_nm": "금융상품명",  # 금융상품명d
        "fin_prdt_cd": "금융상품코드",  # 금융상품코드d
        "join_way": "가입방법",  # 가입방법d
        "loan_inci_expn": "대출부대비용",
        "erly_rpay_fee": "중도상환수수료",
        "dly_rate": "연체이자율",
        "loan_lmt": "대출한도",
        "rpay_type_nm": "대출상환유형",
        "lend_rate_type_nm": "대출금리유형",
        "lend_rate_min": "대출금리최저",
        "lend_rate_max": "대출금리최고",
        "lend_rate_avg": "전월취급평균금리",
        "dcls_strt_day": "공시시작일",  # 공시시작일d
        "dcls_end_day": "공시종료일",  # 공시종료일d
        "dcls_month": "공시제출월",  # 공시제출월d
    }

    jm.values.calculator = {}
    jm.values.calculator.fixed_deposit = [
        "납입액",
        "우대조건",
        "최고한도",
        "저축개월",
        "저축금리유형명",
        "저축금리",
        "최고우대금리",
    ]

    jm.values.calculator.installment_deposit = [
        "납입액",
        "우대조건",
        "최고한도",
        "저축개월",
        "저축금리유형명",
        "저축금리",
        "최고우대금리",
    ]

    jm.values.calculator.jeonse_loan = [
        "대출액",
        "대출한도",
        "대출금리유형",  # 고정금리 # 변동금리
        "대출금리최저",
        "대출금리최고",
    ]

    jm.save(save_path)
