# products/services.py

from django.db.models import Count

from .models import FinProduct


# --- 카테고리 값은 DB에 맞게 수정해서 쓰기 ---
# 예시) category 에
#   "정기예금" / "적금" / "전세자금대출" 이런 식으로 저장되어 있다면,
#   아래 상수를 그 값에 맞게 바꿔줘.
CATEGORY_DEPOSIT = "정기예금"
CATEGORY_SAVING = "적금"
CATEGORY_LOAN = "전세자금대출"


def _get_random_by_category(category: str, limit: int) -> list[FinProduct]:
    """
    특정 category 에서 랜덤으로 limit 개 추출
    """
    return list(FinProduct.objects.filter(category=category).order_by("?")[:limit])


def get_main_recommendations_for_guest() -> list[FinProduct]:
    """
    비로그인 / 로그인 + 북마크 0개일 때 사용할 기본 랜덤 추천
    - 예금 3개, 적금 3개, 대출 4개 → 총 10개
    """
    products: list[FinProduct] = []
    products += _get_random_by_category(CATEGORY_DEPOSIT, 3)
    products += _get_random_by_category(CATEGORY_SAVING, 3)
    products += _get_random_by_category(CATEGORY_LOAN, 4)
    return products


def get_main_recommendations_for_user(user) -> tuple[list[FinProduct], int]:
    """
    로그인한 사용자의 메인 추천 로직

    - 북마크 0  개 → get_main_recommendations_for_guest() 결과 10개
    - 북마크 1~9개 → 북마크 + 랜덤 추천으로 10개 채우기
    - 북마크 10개 이상 →
        사용자가 북마크한 상품 중, 전체 북마크 수가 많은 순으로 TOP 10
    """
    # 사용자가 북마크한 상품들만 추출 (중복 제거)
    bookmarked_qs = FinProduct.objects.filter(bookmark_lists__user=user).distinct()
    bookmark_count = bookmarked_qs.count()

    # 0개 → 게스트용 랜덤 추천 10개
    if bookmark_count == 0:
        return get_main_recommendations_for_guest(), bookmark_count

    # 1~9개 → 나머지 개수만큼 랜덤 추천을 섞어서 10개 맞추기
    if bookmark_count < 10:
        needed = 10 - bookmark_count
        random_qs = FinProduct.objects.exclude(
            bookmark_lists__user=user
        ).order_by(  # 내가 이미 북마크한건 제외
            "?"
        )[
            :needed
        ]
        products = list(bookmarked_qs) + list(random_qs)
        return products, bookmark_count

    # 10개 이상 →
    #  내가 북마크한 상품들 중에서,
    #  전체 북마크 수(bookmark_lists 개수)가 많은 순으로 TOP 10
    popular_qs = bookmarked_qs.annotate(
        bookmark_total=Count("bookmark_lists")
    ).order_by("-bookmark_total", "fin_prdt_nm")[:10]

    return list(popular_qs), bookmark_count
