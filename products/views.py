import random

from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.shortcuts import render

from accounts.models import Bookmark
from products.models import FinProduct
from products.services import (
    get_main_recommendations_for_user,
)


def index(request):
    if request.user.is_authenticated:
        _, bookmark_count = get_main_recommendations_for_user(request.user)

        my_bookmarks = FinProduct.objects.filter(
            fin_prdt_cd__in=Bookmark.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        my_bookmarks = []

    deposits = list(FinProduct.objects.filter(category__icontains="예금"))
    savings = list(FinProduct.objects.filter(category__icontains="적금"))
    loans = list(FinProduct.objects.filter(category__icontains="대출"))

    random_pool = deposits + savings + loans

    # 북마크 3개 이상 → 인기순 TOP3
    if len(my_bookmarks) >= 3:
        products = my_bookmarks.annotate(total_bookmarks_count=models.Count("bookmark_lists")).order_by(
            "-total_bookmarks_count"
        )[:3]
        return render(
            request,
            "products/index.html",
            {
                "products": products,
                "no_bookmarks": False,
            },
        )

    # 북마크 1~2개 → 그대로 + 랜덤 추천 보완
    pick = list(my_bookmarks)
    need = 3 - len(pick)

    if need > 0:
        pool = [p for p in random_pool if p not in pick]
        if pool:
            pick.extend(random.sample(pool, min(need, len(pool))))

    products = pick[:3]

    return render(
        request,
        "products/index.html",
        {
            "products": products,
            "no_bookmarks": len(my_bookmarks) == 0,
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
