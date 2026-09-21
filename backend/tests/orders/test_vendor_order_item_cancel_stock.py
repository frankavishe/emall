import threading

import pytest
from django.db import connections
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

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


@pytest.mark.django_db
def test_cancelling_a_line_restores_exact_quantity_to_stock(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product.id, "quantity": 2}, format="json")
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    product.refresh_from_db()
    assert product.stock_quantity == 8

    _authenticate(api_client, vendor)
    item_id = api_client.get("/api/vendor/order-items").data["results"][0]["id"]

    response = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "CANCELLED"}, format="json"
    )

    assert response.status_code == 200
    product.refresh_from_db()
    assert product.stock_quantity == 10


@pytest.mark.django_db(transaction=True)
def test_concurrent_cancellations_of_different_lines_for_same_product_both_restore_correctly():
    product = ProductFactory(is_published=True, price="9.99", stock_quantity=10)
    vendor = product.shop.owner
    customer_a = UserFactory(role=User.Role.CUSTOMER)
    customer_b = UserFactory(role=User.Role.CUSTOMER)

    client_a = APIClient()
    client_b = APIClient()
    _authenticate(client_a, customer_a)
    _authenticate(client_b, customer_b)
    client_a.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    client_b.post("/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json")
    client_a.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    client_b.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )
    product.refresh_from_db()
    assert product.stock_quantity == 8

    vendor_client = APIClient()
    _authenticate(vendor_client, vendor)
    item_ids = [
        row["id"] for row in vendor_client.get("/api/vendor/order-items").data["results"]
    ]
    assert len(item_ids) == 2

    results = {}
    barrier = threading.Barrier(2)

    def cancel(name, item_id):
        client = APIClient()
        _authenticate(client, vendor)
        barrier.wait()
        try:
            response = client.patch(
                f"/api/vendor/order-items/{item_id}/status",
                {"status": "CANCELLED"},
                format="json",
            )
            results[name] = response.status_code
        finally:
            connections.close_all()

    thread_a = threading.Thread(target=cancel, args=("a", item_ids[0]))
    thread_b = threading.Thread(target=cancel, args=("b", item_ids[1]))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert sorted(results.values()) == [200, 200]
    product.refresh_from_db()
    assert product.stock_quantity == 10
