"""Payment as a swappable service interface (Constitution Principle IV), mirroring
`apps/core/email.py`'s `EmailService` / `DjangoEmailService` / `get_email_service()` pattern
exactly. `charge()` accepts only an opaque `method` label, never raw card fields (Constitution
Principle III) — there is nothing sensitive for a real gateway swap-in to have leaked through
this interface.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


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
