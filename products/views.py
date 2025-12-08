import random

from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.shortcuts import render

from accounts.models import Bookmark
from products.models import FinProduct

def pick_one(queryset):
    """QuerySet에서 랜덤 1개 선택 (빈 경우 None)"""
    items = list(queryset)
    return random.choice(items) if items else None


def index(request):
    """
    메인 화면 추천 금융상품 목록을 생성하는 View.

    사용자 북마크 정보와 금융상품 카테고리를 기반으로
    '최대 3개의 상품'을 노출하는 추천 로직을 처리한다.

    추천 규칙
    ----------
    1) 북마크 3개 이상
        - bookmark_lists 기준으로 인기순(total_bm) 정렬
        - TOP 3 상품만 노출

    2) 북마크 1~2개
        - 기존 북마크 상품을 우선 배치
        - 중복을 제외한 전체 상품(all_products) 중 랜덤으로 부족한 개수 보충
        - 항상 총 3개 유지

    3) 북마크 0개
        - 예금/적금/대출 각 카테고리에서 최대 1개씩 랜덤 추출
        - 특정 카테고리 상품이 없을 수 있으므로 중간에 None 들어올 수 있음
        - 만약 카테고리 랜덤 결과가 3개 미만이면 모든 상품에서 추가 랜덤 보충
        - 최종적으로 항상 총 3개 유지

    내부 로직
    ----------
    - Bookmark → FinProduct(FK: fin_prdt_cd) 매핑하여 내 북마크 상품 조회
    - 중복 방지를 위해 selected 리스트와 picked_ids 세트를 유지
    - pick_from_qs() 서브 함수로 QuerySet에서 랜덤한 상품을 limit 개수만큼 추출
    - 카테고리 우선 / 전체 상품 fallback 구조로 안정적인 추천 보장

    Parameters
    ----------
    request : HttpRequest
        현재 요청 객체. 인증 여부를 통해 북마크 조회 여부를 판단함.

    Returns
    -------
    HttpResponse
        추천된 금융상품 리스트(products)와 북마크 유무(no_bookmarks)를 포함해
        'products/index.html' 템플릿을 렌더링한 응답 객체.

    Notes
    -----
    - FinProduct.fin_prdt_cd는 문자열 PK이므로 중복 제거 시 세트(picked_ids) 사용
    - 카테고리 불균형(예: 적금만 많은 경우)에서도 항상 총 3개가 보장되도록 설계됨
    - 비로그인 사용자는 북마크를 고려하지 않고 카테고리 기반 추천

    Examples
    --------
    북마크 1개인 경우:
        selected = [북마크1] + [랜덤2]

    북마크 0개이고 예금/적금/대출 중 1개 카테고리가 비어 있는 경우:
        selected = [예금1, 적금1, (대출 없음)]
        → all_products에서 랜덤으로 나머지 1개 보충

    """
    # 내 북마크 조회
    if request.user.is_authenticated:
        bookmark_ids = Bookmark.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)

        my_bookmarks_qs = FinProduct.objects.filter(fin_prdt_cd__in=bookmark_ids)
        my_bookmarks = list(my_bookmarks_qs)
    else:
        my_bookmarks_qs = FinProduct.objects.none()
        my_bookmarks = []

    bm_count = len(my_bookmarks)

    # 북마크 3개 이상 → 인기순 TOP3
    if bm_count >= 3:
        products = (
            my_bookmarks_qs
            .annotate(total_bm=models.Count("bookmark_lists"))
            .order_by("-total_bm")[:3]
        )
        return render(
            request,
            "products/index.html",
            {
                "products": products,
                "no_bookmarks": False,
            },
        )

    # 북마크 0~2개 → 카테고리 / 전체 랜덤 조합
    selected: list[FinProduct] = list(my_bookmarks)
    picked_ids = {p.fin_prdt_cd for p in selected}

    def pick_from_qs(qs, limit):
        """주어진 QuerySet에서 아직 안 뽑힌 상품을 최대 limit개 랜덤 선택"""
        pool = qs.exclude(fin_prdt_cd__in=picked_ids)
        ids = list(pool.values_list("fin_prdt_cd", flat=True))
        random.shuffle(ids)
        chosen_ids = ids[:limit]

        picked = list(FinProduct.objects.filter(fin_prdt_cd__in=chosen_ids))
        for p in picked:
            if p.fin_prdt_cd not in picked_ids:
                selected.append(p)
                picked_ids.add(p.fin_prdt_cd)

    # 북마크 0개일 때: 카테고리 우선
    if bm_count == 0:
        deposits = FinProduct.objects.filter(category__icontains="예금")
        savings = FinProduct.objects.filter(category__icontains="적금")
        loans = FinProduct.objects.filter(category__icontains="대출")

        # 카테고리별로 최대 1개씩 시도
        pick_from_qs(deposits, 1)
        pick_from_qs(savings, 1)
        pick_from_qs(loans, 1)

        # 그래도 3개가 안 되면 전체에서 랜덤 보충
        if len(selected) < 3:
            all_products = FinProduct.objects.all()
            pick_from_qs(all_products, 3 - len(selected))

    # 북마크 1~2개일 때: 전체에서 랜덤 보충
    else:
        all_products = FinProduct.objects.all()
        pick_from_qs(all_products, 3 - len(selected))

    products = selected[:3]

    return render(
        request,
        "products/index.html",
        {
            "products": products,
            "no_bookmarks": bm_count == 0,
        },
    )



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
