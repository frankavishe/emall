"""Sending money to shop owners as a swappable service interface (Constitution Principle IV),
mirroring `apps/payments/services.py`. A real mobile-money provider (AzamPay, Selcom, ClickPesa…)
plugs in as another `DisbursementService` selected by the `DISBURSEMENT_BACKEND` setting.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

SUCCEEDED = "SUCCEEDED"
PROCESSING = "PROCESSING"
FAILED = "FAILED"


@dataclass(frozen=True)
class DisbursementResult:
    # SUCCEEDED, PROCESSING (provider will confirm later) or FAILED.
    status: str
    provider_reference: str | None = None
    failure_reason: str = ""


class DisbursementService(ABC):
    @abstractmethod
    def disburse(
        self, *, amount: Decimal, network: str, phone: str, account_name: str, reference: str
    ) -> DisbursementResult: ...


# A payout to this phone number deterministically fails, so the failure path is testable.
MOCK_FAILING_PHONE = "0000000000"


class MockDisbursementService(DisbursementService):
    def disburse(self, *, amount, network, phone, account_name, reference):
        if phone.strip() == MOCK_FAILING_PHONE:
            return DisbursementResult(status=FAILED, failure_reason="Mock: recipient rejected.")
        return DisbursementResult(status=SUCCEEDED, provider_reference=uuid.uuid4().hex)


_BACKENDS = {"mock": MockDisbursementService}


def get_disbursement_service() -> DisbursementService:
    backend = getattr(settings, "DISBURSEMENT_BACKEND", "mock")
    return _BACKENDS[backend]()
