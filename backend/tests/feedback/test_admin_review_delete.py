import pytest

from apps.accounts.models import User
from apps.feedback.models import Review
from tests.factories import ReviewFactory, UserFactory

pytestmark = pytest.mark.django_db


def _authenticate(api_client, user, password="a-strong-password-1"):
    login_response = api_client.post(
        "/api/auth/login", {"email": user.email, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")


def test_admin_deletes_a_review(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    review = ReviewFactory()

    _authenticate(api_client, admin)
    response = api_client.delete(f"/api/admin/reviews/{review.id}")

    assert response.status_code == 204
    assert not Review.objects.filter(pk=review.id).exists()


def test_admin_deleting_the_same_review_twice_404s_on_the_second_call(api_client):
    admin = UserFactory(role=User.Role.ADMINISTRATOR)
    review = ReviewFactory()

    _authenticate(api_client, admin)
    assert api_client.delete(f"/api/admin/reviews/{review.id}").status_code == 204
    assert api_client.delete(f"/api/admin/reviews/{review.id}").status_code == 404


def test_admin_review_delete_rejects_non_administrator(api_client):
    vendor = UserFactory(role=User.Role.VENDOR)
    review = ReviewFactory()

    _authenticate(api_client, vendor)
    response = api_client.delete(f"/api/admin/reviews/{review.id}")

    assert response.status_code == 403
    assert Review.objects.filter(pk=review.id).exists()
