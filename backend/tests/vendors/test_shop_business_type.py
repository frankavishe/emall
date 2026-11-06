import pytest

from apps.accounts.models import User
from apps.vendors.models import Shop
from tests.factories import ProductFactory, ShopFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_new_shop_defaults_to_goods(api_client):
    user = UserFactory(role=User.Role.CUSTOMER)
    api_client.force_authenticate(user=user)

    response = api_client.post("/api/vendor/shops", {"name": "Plain"}, format="json")

    assert response.status_code == 201
    assert response.data["business_type"] == "GOODS"
    assert response.data["booking_capacity"] == 1


def test_a_shop_can_be_requested_as_a_services_business(api_client):
    user = UserFactory(role=User.Role.CUSTOMER)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/vendor/shops", {"name": "Salon", "business_type": "SERVICES"}, format="json"
    )

    assert response.status_code == 201
    assert Shop.objects.get(pk=response.data["id"]).business_type == Shop.BusinessType.SERVICES


def test_unknown_business_type_is_refused(api_client):
    api_client.force_authenticate(user=UserFactory(role=User.Role.CUSTOMER))

    response = api_client.post(
        "/api/vendor/shops", {"name": "Odd", "business_type": "BOTH"}, format="json"
    )

    assert response.status_code == 400


def test_vendor_registration_records_the_business_type(api_client):
    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Asha",
            "email": "asha@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Asha Salon",
            "business_type": "SERVICES",
        },
        format="json",
    )

    assert response.status_code == 201
    assert Shop.objects.get(name="Asha Salon").business_type == Shop.BusinessType.SERVICES
    assert response.data["shops"][0]["business_type"] == "SERVICES"


def test_vendor_registration_defaults_to_goods(api_client):
    response = api_client.post(
        "/api/auth/register/vendor",
        {
            "name": "Juma",
            "email": "juma@example.com",
            "password": "a-strong-password-1",
            "shop_name": "Juma Goods",
        },
        format="json",
    )

    assert response.status_code == 201
    assert Shop.objects.get(name="Juma Goods").business_type == Shop.BusinessType.GOODS


def test_owner_endpoints_cannot_change_the_business_type(api_client):
    shop = ShopFactory()
    api_client.force_authenticate(user=shop.owner)

    for path, body in (
        ("name", {"name": "Renamed", "business_type": "SERVICES"}),
        ("description", {"description": "New", "business_type": "SERVICES"}),
        ("theme", {"primary_color": "#112233", "business_type": "SERVICES"}),
    ):
        assert (
            api_client.patch(f"/api/vendor/shops/{shop.id}/{path}", body, format="json").status_code
            == 200
        )

    shop.refresh_from_db()
    assert shop.business_type == Shop.BusinessType.GOODS


def test_services_shop_cannot_list_a_product(api_client):
    from tests.factories import CategoryFactory, ServicesShopFactory

    shop = ServicesShopFactory()
    api_client.force_authenticate(user=shop.owner)

    response = api_client.post(
        "/api/vendor/products",
        {
            "shop_id": shop.id,
            "name": "Shampoo",
            "price": "100.00",
            "stock_quantity": 1,
            "category": CategoryFactory().slug,
        },
        format="json",
    )

    assert response.status_code == 403


def test_a_goods_product_still_works(api_client):
    product = ProductFactory(is_published=True)

    assert api_client.get(f"/api/catalog/products/{product.id}").status_code == 200
    assert product.shop.business_type == Shop.BusinessType.GOODS
