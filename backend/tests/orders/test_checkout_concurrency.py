import threading

import pytest
from django.db import connections
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orders.models import Order
from tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db(transaction=True)

SHIPPING = {
    "recipient_name": "Ama Owusu",
    "address_line": "12 Ring Road",
    "city": "Accra",
    "region": "Greater Accra",
    "postal_code": "GA-184-9021",
    "country": "Ghana",
    "phone": "+233201234567",
}


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_concurrent_checkouts_never_oversell_a_shared_product():
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=1)
    customer_a = UserFactory(role=User.Role.CUSTOMER)
    customer_b = UserFactory(role=User.Role.CUSTOMER)

    client_a = APIClient()
    client_b = APIClient()
    _authenticate(client_a, customer_a)
    _authenticate(client_b, customer_b)
    client_a.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )
    client_b.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )

    results = {}
    barrier = threading.Barrier(2)

    def checkout(name, client):
        barrier.wait()
        try:
            response = client.post(
                "/api/checkout",
                {"shipping": SHIPPING, "payment_method": "card"},
                format="json",
            )
            results[name] = response.status_code
        finally:
            connections.close_all()

    thread_a = threading.Thread(target=checkout, args=("a", client_a))
    thread_b = threading.Thread(target=checkout, args=("b", client_b))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert sorted(results.values()) == [201, 400]
    product.refresh_from_db()
    assert product.stock_quantity == 0
    assert Order.objects.count() == 1
