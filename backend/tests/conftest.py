import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """DRF's ScopedRateThrottle stores hit counts in the default cache, which otherwise
    persists across tests in the same process and would make login/password-reset/
    verify-email tests bleed into each other's rate limits (Constitution Principle V:
    tests must be independently reliable, not order-dependent)."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def mock_payment_backend(settings):
    """Tests never depend on the developer's backend/.env PAYMENT_BACKEND (which is usually the
    AzamPay simulator locally); payment tests opt in to another backend explicitly."""
    settings.PAYMENT_BACKEND = "mock"
    settings.MOCK_CARD_PAYMENTS_ENABLED = True
    settings.MANUAL_PAYMENT_METHODS = ["cod", "lipa_namba"]
    settings.LIPA_NAMBA_TILL = "123456"
