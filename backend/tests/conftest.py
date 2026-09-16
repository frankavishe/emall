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
