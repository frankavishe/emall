import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.catalog.models import Product
from apps.core.pagination import LimitedPageNumberPagination
from tests.factories import ProductFactory

pytestmark = pytest.mark.django_db

request_factory = APIRequestFactory()


def _paginate(query_string=""):
    ProductFactory.create_batch(25)
    queryset = Product.objects.order_by("-created_at")
    request = Request(request_factory.get(f"/fake{query_string}"))
    paginator = LimitedPageNumberPagination()
    return paginator.paginate_queryset(queryset, request)


def test_default_page_size_unchanged_when_page_size_omitted():
    page = _paginate()
    assert len(page) == 20


def test_page_size_query_param_is_honored():
    page = _paginate("?page_size=5")
    assert len(page) == 5


def test_page_size_is_capped_at_max_page_size():
    page = _paginate("?page_size=100")
    assert len(page) == 24
