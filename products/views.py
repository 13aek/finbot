from django.shortcuts import render
from django.db.models import Q
from .models import FinProduct

# Create your views here.

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
    return render(request, "products/search.html")


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
        
    query = request.GET.get("q", "")
    results = []

    if query:
        results = FinProduct.objects.filter(
            Q(product_name__icontains=query) |
            Q(company_name__icontains=query)
        )

    context = {
        "query": query,
        "results": results
        }
    return render(request, "products/search.html", context)