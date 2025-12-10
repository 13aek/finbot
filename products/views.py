import random

from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.shortcuts import render

from accounts.models import Bookmark
from products.models import FinProduct


# 추천 상품 로직
def recommend_products(request):
    """
    추천 로직:

    1) 비로그인 사용자 and 로그인 + 북마크 0개
       → 적금 예금 대출 카테고리별로 랜덤 1개씩

    2) 로그인 + 북마크 1개 이상
       → 추천 섹션 없도록 빈 리스트 반환
       index 뷰에서 처리
    """

    # 로그인 상태에서 북마크 개수 계산
    bookmark_count = 0
    if request.user.is_authenticated:
        bookmark_count = Bookmark.objects.filter(user=request.user).count()

    # 로그인 + 북마크 1개 이상 → 추천 X
    if request.user.is_authenticated and bookmark_count > 0:
        return []

    # 비로그인 or 북마크 0개 → 랜덤추천 3개
    selected = []
    picked_ids = set()

    def pick_random(qs, k):
        pool = qs.exclude(fin_prdt_cd__in=picked_ids)
        ids = list(pool.values_list("fin_prdt_cd", flat=True))
        random.shuffle(ids)
        chosen = ids[:k]
        result = list(FinProduct.objects.filter(fin_prdt_cd__in=chosen))
        for p in result:
            picked_ids.add(p.fin_prdt_cd)
        return result

    # 카테고리별 랜덤 추출
    deposits = FinProduct.objects.filter(category="fixed_deposit")
    savings = FinProduct.objects.filter(category="installment_deposit")
    loans = FinProduct.objects.filter(category="jeonse_loan")

    selected += pick_random(deposits, 1)
    selected += pick_random(savings, 1)
    selected += pick_random(loans, 1)

    return selected[:3]


def index(request):
    """
    메인 검색 페이지를 렌더링

    사용자가 금융상품명을 입력할 수 있는 검색창을 표시
    검색 실행은 GET 요청으로 'search' 뷰에 전달되며,
    이 함수 자체는 별도의 데이터 조회 로직 없이 템플릿만 반환

    Args:
        request(HttpRequest): 클라이언트의 요청 객체

    Returns:
        HttpResponse: 검색창이 포함된 'products/search.html' 템플릿 렌더링 결과
    """
    bookmarked = []
    if request.user.is_authenticated:
        bookmarked = request.user.products.all()
    # return render(request, "products/index.html", {"bookmarked": bookmarked})
    # 페이지당 상품 수: 3
    # 페이지네이션 그룹 단위: 10
    paginator = Paginator(bookmarked, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    current_page = page_obj.number
    start_page = ((current_page - 1) // 10) * 10 + 1
    end_page = min(start_page + 9, paginator.num_pages)

    previous_page = max(current_page - 1, 1)
    next_page = min(current_page + 1, paginator.num_pages)

    recommended_products = recommend_products(request)

    show_previous_10 = current_page > 1  # 이전 10개 버튼을 표시할지 여부
    show_next_10 = current_page < paginator.num_pages
    context = {
        "page_obj": page_obj,
        "start_page": start_page,
        "end_page": end_page,
        "previous_page": previous_page,
        "next_page": next_page,
        "show_previous_10": show_previous_10,
        "show_next_10": show_next_10,
        "recommended_products": recommended_products,
    }
    return render(request, "products/index.html", context)


def search(request):
    """
    금융상품명 또는 회사명으로 금융상품을 검색

    GET 요청의 'q' 파라미터를 통해 검색어를 입력받고,
    해당 검색어가 포함된 상품명(product_name) 또는
    회사명(company_name)을 가진 금융상품을 조회

    Args:
        request(HttpRequest): 클라이언트의 요청 객체

    Returns:
        HttpResponse: 검색어(query)와 검색 결과(results)를
        포함한 'products/search.html' 템플릿 렌더링 결과
    """

    query = request.GET.get("query", "")
    clean_query = query.replace(" ", "")
    results = []

    if query:
        results = (
            FinProduct.objects.annotate(
                product=Replace("fin_prdt_nm", Value(" "), Value("")),
                company=Replace("kor_co_nm", Value(" "), Value("")),
            )
            .filter(Q(product__icontains=clean_query) | Q(company__icontains=clean_query))
            .order_by("fin_prdt_cd")
        )
    # 페이지당 상품 수: 5
    # 페이지네이션 그룹 단위: 10
    paginator = Paginator(results, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    current_page = page_obj.number
    start_page = ((current_page - 1) // 10) * 10 + 1
    end_page = min(start_page + 9, paginator.num_pages)

    previous_page = max(current_page - 1, 1)
    next_page = min(current_page + 1, paginator.num_pages)

    show_previous_10 = current_page > 1  # 이전 10개 버튼을 표시할지 여부
    show_next_10 = current_page < paginator.num_pages
    context = {
        "query": query,
        "page_obj": page_obj,
        "start_page": start_page,
        "end_page": end_page,
        "previous_page": previous_page,
        "next_page": next_page,
        "show_previous_10": show_previous_10,
        "show_next_10": show_next_10,
    }
    return render(request, "products/search.html", context)


def product_detail(request, fin_prdt_cd):
    """
    금융상품 상세 페이지 렌더링 뷰

    이 뷰는 금융상품(FinProduct)의 기본 정보와 관련된 옵션 테이블
    (정기예금 옵션, 적금 옵션, 전세자금대출 옵션)을 하나의 상세 페이지에서
    모두 조회 및 출력하기 위한 데이터 전처리 로직을 포함

    주요 처리 로직
    ----------------
    1. 기본 상품(FinProduct) 객체 조회
       - fin_prdt_cd(PK)로 단일 상품 객체 조회
       - ForeignKey 필드를 제외한 모든 단일 필드 값을 검사하여
       None, "None", "null" 등의 값은 빈 문자열("")로 치환

    2. 옵션 테이블 데이터 조회 및 전처리
       - product.fixed_options, installment_options, jeonse_options를
       각각 list로 치환
       - 각 옵션의 단일 필드 값 또한 None / 문자열 None 계열 값을 공백으로 변환

    3. 템플릿 전달
       - 기본 정보: product
       - 옵션 정보: fixed_options / installment_options / jeonse_options

    Args:
        request (HttpRequest): 클라이언트 요청 객체
        fin_prdt_cd (str): 금융상품 기본 코드(PK)

    Returns:
        HttpResponse: 전처리된 상품 정보 및 옵션 데이터를 포함한 상세 페이지 렌더링 결과
    """
    product = FinProduct.objects.get(fin_prdt_cd=fin_prdt_cd)

    # 공통 필드 전처리
    for field in product._meta.fields:
        if field.is_relation:
            continue

        value = getattr(product, field.name)
        if value in [None, "None", "none", "NULL", "null"]:
            setattr(product, field.name, "")

    # 옵션 테이블 조회
    fixed = list(product.fixed_options.all())
    inst = list(product.installment_options.all())
    jeonse = list(product.jeonse_options.all())

    # 옵션 테이블 전처리
    for option_list in [fixed, inst, jeonse]:
        for opt in option_list:
            for f in opt._meta.fields:
                if f.is_relation:
                    continue

                val = getattr(opt, f.name)
                if val in [None, "None", "none", "NULL", "null"]:
                    setattr(opt, f.name, "")
    context = {
        "product": product,
        "fixed_options": fixed,
        "installment_options": inst,
        "jeonse_options": jeonse,
    }

    return render(request, "products/product_detail.html", context)
