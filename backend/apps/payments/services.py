"""Payment as a swappable service interface (Constitution Principle IV), mirroring
`apps/core/email.py`'s `EmailService` / `DjangoEmailService` / `get_email_service()` pattern
exactly. `charge()` accepts only an opaque `method` label, never raw card fields (Constitution
Principle III) — there is nothing sensitive for a real gateway swap-in to have leaked through
this interface.
"""

import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    transaction_reference: str | None = None


class PaymentService(ABC):
    @abstractmethod
    def charge(self, *, amount: Decimal, method: str) -> PaymentResult:
        ...


class MockPaymentService(PaymentService):
    """Succeeds for any `method` value except the case-insensitive sentinel `"declined"`, which
    deterministically fails (research.md §5) — gives FR-016's failure path something concrete and
    repeatable to test against without a real gateway.
    """

    def charge(self, *, amount: Decimal, method: str) -> PaymentResult:
        if method.strip().lower() == "declined":
            return PaymentResult(success=False)
        return PaymentResult(success=True, transaction_reference=uuid.uuid4().hex)


def get_payment_service() -> PaymentService:
    return MockPaymentService()


# --- Mobile money (AzamPay MNO checkout) -------------------------------------------------------
# Asynchronous: `initiate()` only asks the provider to send a USSD push to the customer's phone.
# The outcome arrives later through the AzamPay callback (apps.payments.outcomes).

MOBILE_MONEY_METHOD = "mobile_money"


@dataclass(frozen=True)
class InitiationResult:
    accepted: bool
    provider_reference: str = ""
    message: str = ""


class MobileMoneyGateway(ABC):
    @abstractmethod
    def initiate(
        self, *, amount: Decimal, msisdn: str, provider: str, external_id: str
    ) -> InitiationResult: ...


# The simulator rejects a push to any number ending in this, like AzamPay does for an account
# that can't be charged, so the "push refused" path is testable.
SIMULATOR_REJECTED_SUFFIX = "0000"


class AzamPaySimulatorGateway(MobileMoneyGateway):
    """Stands in for the AzamPay sandbox without credentials. The push "reaches the phone" by
    simply staying PENDING; the dev phone page (`/api/dev/azampay-sim/...`) then approves or
    rejects it by feeding an AzamPay-shaped callback through the real callback handler."""

    def initiate(self, *, amount, msisdn, provider, external_id):
        if msisdn.endswith(SIMULATOR_REJECTED_SUFFIX):
            return InitiationResult(accepted=False, message="Simulator: invalid account number.")
        return InitiationResult(
            accepted=True,
            provider_reference=f"SIM{uuid.uuid4().hex[:16].upper()}",
            message="Simulator: push sent to phone.",
        )


def _azampay_gateway():
    from apps.payments.azampay import AzamPayGateway

    return AzamPayGateway()


_MOBILE_MONEY_BACKENDS = {
    "azampay_simulator": AzamPaySimulatorGateway,
    "azampay": _azampay_gateway,
}


def mobile_money_enabled() -> bool:
    return getattr(settings, "PAYMENT_BACKEND", "mock") in _MOBILE_MONEY_BACKENDS


def simulator_enabled() -> bool:
    return getattr(settings, "PAYMENT_BACKEND", "mock") == "azampay_simulator"


def get_mobile_money_gateway() -> MobileMoneyGateway:
    return _MOBILE_MONEY_BACKENDS[settings.PAYMENT_BACKEND]()


def azampay_amount(amount: Decimal) -> str:
    """The amount as AzamPay takes it: whole shillings, as a string."""

    return str(int(amount.quantize(Decimal("1"))))


_TZ_MOBILE = re.compile(r"^(?:\+?255|0)?([67]\d{8})$")


def normalise_msisdn(raw: str) -> str | None:
    """`0712345678`, `712345678`, `+255712345678` or `255712345678` (spaces/dashes allowed) ->
    `255712345678`; anything that isn't a Tanzanian mobile number -> None."""

    match = _TZ_MOBILE.match(re.sub(r"[\s-]", "", raw or ""))
    return f"255{match.group(1)}" if match else None
