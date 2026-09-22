import pytest
from django.core import mail

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

# `transaction=True` is required: `transaction.on_commit()` callbacks (research.md §1) only fire
# on a real commit, which pytest-django's default savepoint-wrapped test transaction never
# performs.
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


def _place_order_line(api_client, customer, vendor, product=None):
    shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)
    if product is None:
        product = ProductFactory(shop=shop, is_published=True, price="9.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": 1}, format="json"
    )
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    _authenticate(api_client, vendor)
    results = api_client.get("/api/vendor/order-items").data["results"]
    item_id = next(r["id"] for r in results if r["product"]["id"] == product.id)
    return item_id, product


def test_shipped_and_delivered_each_send_one_correctly_addressed_email(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor = UserFactory(role=User.Role.VENDOR)
    item_id, product = _place_order_line(api_client, customer, vendor)

    response = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "PROCESSING"}, format="json"
    )
    assert response.status_code == 200
    order_id = response.data["order_id"]

    response = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "SHIPPED"}, format="json"
    )
    assert response.status_code == 200

    assert len(mail.outbox) == 2  # one for PROCESSING (US3), one for SHIPPED
    shipped_email = mail.outbox[-1]
    assert shipped_email.to == [customer.email]
    assert shipped_email.subject == "Your order has shipped"
    assert str(order_id) in shipped_email.body
    assert product.name in shipped_email.body

    response = api_client.patch(
        f"/api/vendor/order-items/{item_id}/status", {"status": "DELIVERED"}, format="json"
    )
    assert response.status_code == 200

    assert len(mail.outbox) == 3
    delivered_email = mail.outbox[-1]
    assert delivered_email.to == [customer.email]
    assert delivered_email.subject == "Your order has been delivered"
    assert str(order_id) in delivered_email.body
    assert product.name in delivered_email.body

    # Each transition sent its own separate email, never a combined summary.
    subjects = [m.subject for m in mail.outbox]
    assert subjects == [
        "Your order is being prepared",
        "Your order has shipped",
        "Your order has been delivered",
    ]


def test_two_vendors_on_one_order_each_get_notified_only_for_their_own_item(api_client):
    customer = UserFactory(role=User.Role.CUSTOMER)
    vendor_a = UserFactory(role=User.Role.VENDOR)
    vendor_b = UserFactory(role=User.Role.VENDOR)

    shop_a = ShopFactory(owner=vendor_a, status=Shop.Status.APPROVED)
    shop_b = ShopFactory(owner=vendor_b, status=Shop.Status.APPROVED)
    product_a = ProductFactory(shop=shop_a, is_published=True, price="9.99", stock_quantity=10)
    product_b = ProductFactory(shop=shop_b, is_published=True, price="14.99", stock_quantity=10)

    _authenticate(api_client, customer)
    api_client.post("/api/cart/items", {"product_id": product_a.id, "quantity": 1}, format="json")
    api_client.post("/api/cart/items", {"product_id": product_b.id, "quantity": 1}, format="json")
    api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )

    _authenticate(api_client, vendor_a)
    item_a_id = next(
        r["id"]
        for r in api_client.get("/api/vendor/order-items").data["results"]
        if r["product"]["id"] == product_a.id
    )
    api_client.patch(
        f"/api/vendor/order-items/{item_a_id}/status", {"status": "PROCESSING"}, format="json"
    )
    api_client.patch(
        f"/api/vendor/order-items/{item_a_id}/status", {"status": "SHIPPED"}, format="json"
    )

    _authenticate(api_client, vendor_b)
    item_b_id = next(
        r["id"]
        for r in api_client.get("/api/vendor/order-items").data["results"]
        if r["product"]["id"] == product_b.id
    )
    api_client.patch(
        f"/api/vendor/order-items/{item_b_id}/status", {"status": "PROCESSING"}, format="json"
    )
    api_client.patch(
        f"/api/vendor/order-items/{item_b_id}/status", {"status": "SHIPPED"}, format="json"
    )
    response = api_client.patch(
        f"/api/vendor/order-items/{item_b_id}/status", {"status": "DELIVERED"}, format="json"
    )
    assert response.status_code == 200

    assert len(mail.outbox) == 5
    bodies = [m.body for m in mail.outbox]
    a_mentions = [b for b in bodies if product_a.name in b]
    b_mentions = [b for b in bodies if product_b.name in b]
    assert len(a_mentions) == 2
    assert len(b_mentions) == 3
    # Never a single email mentioning both vendors' products.
    assert not any(product_a.name in b and product_b.name in b for b in bodies)
