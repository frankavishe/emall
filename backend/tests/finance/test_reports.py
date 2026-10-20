from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader

from apps.accounts.models import User
from apps.finance import reports
from apps.finance.services import filter_transactions
from apps.orders.models import OrderItem
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop
from tests.factories import OrderItemFactory, ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _shop(name):
    return ShopFactory(
        name=name,
        status=Shop.Status.APPROVED,
        payout_network=Shop.PayoutNetwork.MPESA,
        payout_phone="+255712345678",
        payout_account_name="Juma Shop",
    )


def _line(shop, status=OrderItem.Status.DELIVERED):
    return OrderItemFactory(
        product=ProductFactory(shop=shop, is_published=True),
        unit_price=Decimal("100.00"),
        commission_rate="10.00",
        commission_amount="10.00",
        vendor_earning="90.00",
        status=status,
    )


def _pay(line, reference, status=PaymentRecord.Status.SUCCEEDED, method="card"):
    return PaymentRecord.objects.create(
        order=line.order,
        method=method,
        amount="100.00",
        status=status,
        transaction_reference=reference,
    )


def _pdf_text(response):
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith('attachment; filename="mangimall-')
    assert response.content.startswith(b"%PDF")
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)


@pytest.fixture
def admin_client(api_client):
    api_client.force_authenticate(UserFactory(role=User.Role.ADMINISTRATOR))
    return api_client


def test_finance_report_lists_every_shop(admin_client):
    # More shops than one page of the JSON endpoint holds.
    for index in range(25):
        _line(_shop(f"Duka {index:02d}"))

    text = _pdf_text(admin_client.get("/api/admin/finance/report.pdf?from=2020-01-01"))

    assert "Finance summary" in text
    assert "2020-01-01 to today" in text
    assert "Duka 00" in text and "Duka 24" in text


def test_finance_report_rejects_bad_dates(admin_client):
    assert admin_client.get("/api/admin/finance/report.pdf?from=yesterday").status_code == 400


def test_transactions_report_applies_filters(admin_client):
    shop = _shop("Duka")
    _pay(_line(shop), "ref-paid")
    _pay(_line(shop), "ref-failed", status=PaymentRecord.Status.FAILED)

    text = _pdf_text(admin_client.get("/api/admin/transactions/report.pdf?status=SUCCEEDED"))

    assert "ref-paid" in text
    assert "ref-failed" not in text
    assert "Status: Succeeded" in text
    assert "TZS 100" in text


def test_filter_transactions_matches_json_filters():
    shop = _shop("Duka")
    paid = _pay(_line(shop), "ref-a", method="cod")
    _pay(_line(shop), "ref-b", method="card")

    assert list(filter_transactions(method="cod")) == [paid]
    assert list(filter_transactions(search="ref-a")) == [paid]
    assert paid in filter_transactions(search=str(paid.order_id))
    assert filter_transactions(status="NOT-A-STATUS").count() == 2


def test_report_row_limit_adds_notice(admin_client, monkeypatch):
    monkeypatch.setattr(reports, "REPORT_ROW_LIMIT", 1)
    shop = _shop("Duka")
    _pay(_line(shop), "ref-a")
    _pay(_line(shop), "ref-b")

    text = _pdf_text(admin_client.get("/api/admin/transactions/report.pdf"))

    assert "Only the first 1 rows are shown" in text


def test_payout_reports(admin_client):
    shop = _shop("Duka la Juma")
    _line(shop)
    payout = admin_client.post(f"/api/admin/shops/{shop.id}/payouts").data

    listing = _pdf_text(admin_client.get(f"/api/admin/payouts/report.pdf?shop={shop.id}"))
    assert payout["reference"] in listing
    assert "Shop: Duka la Juma" in listing

    statement = _pdf_text(admin_client.get(f"/api/admin/payouts/{payout['id']}/report.pdf"))
    assert payout["reference"] in statement
    assert "M-Pesa" in statement
    assert "TZS 90" in statement

    assert admin_client.get("/api/admin/payouts/999999/report.pdf").status_code == 404


def test_vendor_earnings_report_shows_only_own_shops(api_client):
    mine = _shop("My Duka")
    theirs = _shop("Their Duka")
    _line(mine)
    _line(theirs)
    owner = mine.owner
    owner.is_vendor = True
    owner.save()
    api_client.force_authenticate(owner)

    text = _pdf_text(api_client.get("/api/vendor/earnings/report.pdf"))
    assert "My Duka" in text
    assert "Their Duka" not in text

    other = _pdf_text(api_client.get(f"/api/vendor/earnings/report.pdf?shop={theirs.id}"))
    assert "Their Duka" not in other


def test_vendor_earnings_report_forbids_customers(api_client):
    api_client.force_authenticate(UserFactory())
    assert api_client.get("/api/vendor/earnings/report.pdf").status_code == 403
