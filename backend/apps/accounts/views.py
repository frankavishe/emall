"""Shared token-issuance plumbing (task T014).

Not a routed endpoint on its own — reused by the register/login/refresh views built in later
phases. Access tokens go in the JSON response body only (held in memory on the frontend); refresh
tokens are set *exclusively* as an httpOnly/Secure/SameSite cookie, never in a JSON body
(Constitution Principle III, research.md §1).
"""

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


class TokenResponseMixin:
    """Issues a simplejwt access/refresh pair and puts each half where it belongs."""

    def issue_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        return access, str(refresh)

    def set_refresh_cookie(self, response, refresh_token):
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )

    def clear_refresh_cookie(self, response):
        response.delete_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        )

    def get_refresh_token_from_cookie(self, request):
        return request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
