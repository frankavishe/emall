from decimal import Decimal

import pytest
import requests

from apps.payments import azampay
from apps.payments.azampay import AzamPayGateway
from apps.payments.services import normalise_msisdn

pytestmark = pytest.mark.django_db


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._body

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def azampay_settings(settings):
    settings.AZAMPAY_AUTH_URL = "https://auth.example"
    settings.AZAMPAY_API_URL = "https://api.example"
    settings.AZAMPAY_APP_NAME = "emall"
    settings.AZAMPAY_CLIENT_ID = "client"
    settings.AZAMPAY_CLIENT_SECRET = "secret"
    settings.AZAMPAY_API_KEY = "key"


@pytest.fixture
def fake_post(monkeypatch):
    """Scripted `requests.post`: responses are popped per URL, every call is recorded."""

    calls = []
    script = {}

    def post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers or {}})
        outcome = script[url].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(azampay.requests, "post", post)
    return calls, script


TOKEN_URL = "https://auth.example/AppRegistration/GenerateToken"
CHECKOUT_URL = "https://api.example/azampay/mno/checkout"


def _token(value="tok-1"):
    return FakeResponse(200, {"data": {"accessToken": value, "expire": "2999-01-01T00:00:00Z"}})


def _initiate(amount="12000.00"):
    return AzamPayGateway().initiate(
        amount=Decimal(amount), msisdn="255712345678", provider="Mpesa", external_id="ref-1"
    )


def test_initiate_sends_azampay_checkout_and_caches_token(fake_post):
    calls, script = fake_post
    script[TOKEN_URL] = [_token()]
    script[CHECKOUT_URL] = [
        FakeResponse(200, {"success": True, "transactionId": "AZ-9", "message": "ok"}),
        FakeResponse(200, {"success": True, "transactionId": "AZ-10", "message": "ok"}),
    ]

    first = _initiate()
    second = _initiate()

    assert first.accepted and first.provider_reference == "AZ-9"
    assert second.provider_reference == "AZ-10"
    assert [call["url"] for call in calls].count(TOKEN_URL) == 1
    checkout = calls[1]
    assert checkout["headers"] == {"Authorization": "Bearer tok-1", "X-API-Key": "key"}
    assert checkout["json"] == {
        "accountNumber": "255712345678",
        "amount": "12000",
        "currency": "TZS",
        "externalId": "ref-1",
        "provider": "Mpesa",
    }


def test_initiate_refreshes_token_once_on_401(fake_post):
    calls, script = fake_post
    script[TOKEN_URL] = [_token("old"), _token("new")]
    script[CHECKOUT_URL] = [
        FakeResponse(401, {"message": "expired"}),
        FakeResponse(200, {"success": True, "transactionId": "AZ-1"}),
    ]

    result = _initiate()

    assert result.accepted
    assert calls[-1]["headers"]["Authorization"] == "Bearer new"


def test_initiate_maps_rejection_and_network_errors(fake_post):
    _, script = fake_post
    script[TOKEN_URL] = [_token()]
    script[CHECKOUT_URL] = [
        FakeResponse(400, {"success": False, "message": "Invalid provider"}),
        requests.ConnectionError("down"),
    ]

    rejected = _initiate()
    unreachable = _initiate()

    assert not rejected.accepted and rejected.message == "Invalid provider"
    assert not unreachable.accepted and unreachable.message == "Payment provider unavailable."


def test_initiate_fails_cleanly_when_token_request_fails(fake_post):
    _, script = fake_post
    script[TOKEN_URL] = [FakeResponse(401, {"message": "bad credentials"})]

    result = _initiate()

    assert not result.accepted


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0712345678", "255712345678"),
        ("712345678", "255712345678"),
        ("+255 712 345 678", "255712345678"),
        ("255-655-123-456", "255655123456"),
        ("0812345678", None),
        ("071234567", None),
        ("", None),
    ],
)
def test_normalise_msisdn(raw, expected):
    assert normalise_msisdn(raw) == expected
