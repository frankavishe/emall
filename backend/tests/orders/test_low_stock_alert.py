from unittest import mock

import pytest
from django.core import mail

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory
from tests.orders.test_checkout_success import SHIPPING, _authenticate

pytestmark = pytest.mark.django_db


def _checkout(api_client, product, quantity):
    api_client.post(
        "/api/cart/items", {"product_id": product.id, "quantity": quantity}, format="json"
    )
    return api_client.post(
        "/api/checkout", {"shipping": SHIPPING, "payment_method": "card"}, format="json"
    )


def _low_stock_emails():
    return [m for m in mail.outbox if "stock:" in m.subject]


@pytest.fixture
def customer(api_client):
    user = UserFactory(role=User.Role.CUSTOMER)
    _authenticate(api_client, user)
    return user


def test_sale_crossing_threshold_emails_the_vendor_once(
    api_client, customer, django_capture_on_commit_callbacks, settings
):
    settings.LOW_STOCK_THRESHOLD = 5
    product = ProductFactory(
        shop=ShopFactory(status=Shop.Status.APPROVED), is_published=True, stock_quantity=6
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = _checkout(api_client, product, 1)

    assert response.status_code == 201
    emails = _low_stock_emails()
    assert len(emails) == 1
    assert emails[0].subject == f'Low stock: "{product.name}"'
    assert emails[0].to == [product.shop.owner.email]
    assert "only 5 left" in emails[0].body


def test_sale_of_already_low_product_sends_no_email(
    api_client, customer, django_capture_on_commit_callbacks, settings
):
    settings.LOW_STOCK_THRESHOLD = 5
    product = ProductFactory(
        shop=ShopFactory(status=Shop.Status.APPROVED), is_published=True, stock_quantity=5
    )

    with django_capture_on_commit_callbacks(execute=True):
        _checkout(api_client, product, 1)

    assert _low_stock_emails() == []


def test_selling_out_sends_out_of_stock_email(
    api_client, customer, django_capture_on_commit_callbacks, settings
):
    settings.LOW_STOCK_THRESHOLD = 5
    product = ProductFactory(
        shop=ShopFactory(status=Shop.Status.APPROVED), is_published=True, stock_quantity=3
    )

    with django_capture_on_commit_callbacks(execute=True):
        _checkout(api_client, product, 3)

    emails = _low_stock_emails()
    assert len(emails) == 1
    assert emails[0].subject == f'Out of stock: "{product.name}"'


def test_email_failure_does_not_fail_checkout(
    api_client, customer, django_capture_on_commit_callbacks, settings
):
    settings.LOW_STOCK_THRESHOLD = 5
    product = ProductFactory(
        shop=ShopFactory(status=Shop.Status.APPROVED), is_published=True, stock_quantity=6
    )

    with mock.patch(
        "apps.core.email.DjangoEmailService.send_low_stock_email", side_effect=RuntimeError
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = _checkout(api_client, product, 2)

    assert response.status_code == 201
    product.refresh_from_db()
    assert product.stock_quantity == 4
