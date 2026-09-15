import pytest
from django.test import RequestFactory

from apps.accounts.models import User
from apps.vendors.models import Shop
from apps.vendors.permissions import IsApprovedShopOwner
from tests.factories import ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def _request_as(user):
    request = RequestFactory().get("/")
    request.user = user
    return request


def test_approved_shop_permitted_for_its_owner():
    vendor = UserFactory(role=User.Role.VENDOR)
    approved_shop = ShopFactory(owner=vendor, status=Shop.Status.APPROVED)

    assert IsApprovedShopOwner().has_object_permission(
        _request_as(vendor), view=None, obj=approved_shop
    )


def test_pending_shop_denied_for_its_own_owner():
    vendor = UserFactory(role=User.Role.VENDOR)
    pending_shop = ShopFactory(owner=vendor, status=Shop.Status.PENDING)

    assert not IsApprovedShopOwner().has_object_permission(
        _request_as(vendor), view=None, obj=pending_shop
    )


def test_approved_shop_denied_for_a_different_vendor():
    owner = UserFactory(role=User.Role.VENDOR)
    other_vendor = UserFactory(role=User.Role.VENDOR)
    approved_shop = ShopFactory(owner=owner, status=Shop.Status.APPROVED)

    assert not IsApprovedShopOwner().has_object_permission(
        _request_as(other_vendor), view=None, obj=approved_shop
    )


def test_approved_shop_denied_for_non_vendor_role():
    owner = UserFactory(role=User.Role.VENDOR)
    customer = UserFactory(role=User.Role.CUSTOMER)
    approved_shop = ShopFactory(owner=owner, status=Shop.Status.APPROVED)

    assert not IsApprovedShopOwner().has_object_permission(
        _request_as(customer), view=None, obj=approved_shop
    )
