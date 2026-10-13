"""The real AzamPay MNO checkout client (https://developerdocs.azampay.co.tz). Selected with
`PAYMENT_BACKEND=azampay`; sandbox vs live is just `AZAMPAY_AUTH_URL` / `AZAMPAY_API_URL`.

Re-check the request/response field names against the docs when credentials are issued — this
module and `outcomes.handle_azampay_callback()` are the only places that know AzamPay's shapes.
"""

import logging
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from apps.payments.services import InitiationResult, MobileMoneyGateway, azampay_amount

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
TOKEN_CACHE_KEY = "azampay:access_token"
# Refresh the token this long before AzamPay says it expires.
TOKEN_EXPIRY_MARGIN_SECONDS = 60
# Used when AzamPay's `expire` can't be parsed.
DEFAULT_TOKEN_TTL_SECONDS = 30 * 60


class AzamPayError(Exception):
    pass


def _token_ttl(expire):
    try:
        expires_at = datetime.fromisoformat(str(expire).replace("Z", "+00:00"))
    except ValueError:
        return DEFAULT_TOKEN_TTL_SECONDS
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    remaining = (expires_at - datetime.now(UTC)).total_seconds()
    return max(int(remaining) - TOKEN_EXPIRY_MARGIN_SECONDS, 0)


class AzamPayGateway(MobileMoneyGateway):
    def _fetch_token(self):
        try:
            response = requests.post(
                f"{settings.AZAMPAY_AUTH_URL}/AppRegistration/GenerateToken",
                json={
                    "appName": settings.AZAMPAY_APP_NAME,
                    "clientId": settings.AZAMPAY_CLIENT_ID,
                    "clientSecret": settings.AZAMPAY_CLIENT_SECRET,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()["data"]
            token = data["accessToken"]
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            raise AzamPayError(f"Could not get an AzamPay token: {error}") from error

        ttl = _token_ttl(data.get("expire"))
        if ttl > 0:
            cache.set(TOKEN_CACHE_KEY, token, ttl)
        return token

    def _token(self, *, refresh=False):
        if not refresh:
            token = cache.get(TOKEN_CACHE_KEY)
            if token:
                return token
        return self._fetch_token()

    def _checkout(self, token, payload):
        return requests.post(
            f"{settings.AZAMPAY_API_URL}/azampay/mno/checkout",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": settings.AZAMPAY_API_KEY,
            },
            timeout=TIMEOUT_SECONDS,
        )

    def initiate(self, *, amount, msisdn, provider, external_id):
        payload = {
            "accountNumber": msisdn,
            "amount": azampay_amount(amount),
            "currency": "TZS",
            "externalId": external_id,
            "provider": provider,
        }
        try:
            response = self._checkout(self._token(), payload)
            if response.status_code == 401:
                cache.delete(TOKEN_CACHE_KEY)
                response = self._checkout(self._token(refresh=True), payload)
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError(f"unexpected response body {body!r}")
        except (AzamPayError, requests.RequestException, ValueError) as error:
            logger.error("AzamPay checkout for %s failed: %s", external_id, error)
            return InitiationResult(accepted=False, message="Payment provider unavailable.")

        if response.ok and body.get("success"):
            return InitiationResult(
                accepted=True,
                provider_reference=str(body.get("transactionId") or ""),
                message=str(body.get("message") or ""),
            )
        logger.warning(
            "AzamPay rejected checkout %s (HTTP %s): %s", external_id, response.status_code, body
        )
        return InitiationResult(
            accepted=False, message=str(body.get("message") or "Payment request was rejected.")
        )
