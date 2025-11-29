import re

def parse_money_to_int(value):
    """
    다양한 한국어 금액 표현을 모두 int(원 단위)로 변환한다.
    
    지원 예:
    "2억", "2억원", "2000만", "3만 5천", "2,000,000", "350만 원", 1000000 …
    """

    # 이미 숫자형이면 바로 처리
    if isinstance(value, int) or isinstance(value, float):
        return int(value)

    if not isinstance(value, str):
        raise ValueError("지원하지 않는 타입입니다.")

    s = value.strip()
    s = s.replace(",", "")  # 콤마 제거

    # ------------------------
    # 순수 숫자만 있는 경우 (ex: "2000000")
    # ------------------------
    if s.isdigit():
        return int(s)

    # ------------------------
    # 한글 단위 처리
    # 억, 천, 백, 십, 만 단위 지원
    # ------------------------
    # 패턴을 단위별로 정의
    units = {
        "억": 100_000_000,
        "천만": 10_000_000,
        "백만": 1_000_000,
        "십만": 100_000,
        "만": 10_000,
        "천": 1_000,
        "백": 100,
        "십": 10,
    }

    total = 0

    # ex) "1억 2천만 3백만 5천원"
    # 단위마다 찾아서 누적
    for unit, multiplier in units.items():
        pattern = r"(\d+)\s*" + unit
        match = re.search(pattern, s)
        if match:
            num = int(match.group(1))
            total += num * multiplier
            s = re.sub(pattern, "", s)  # 처리한 부분 제거

    # ------------------------
    # 마지막 남은 숫자가 있으면 원 단위로 처리
    # ex) "3만 5000" → "5000" 남음
    # ------------------------
    leftover = re.findall(r"\d+", s)
    if leftover:
        total += int(leftover[0])

    return int(total)
