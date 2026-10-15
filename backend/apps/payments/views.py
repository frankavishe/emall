import hmac
import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import PaymentRecord
from apps.payments.outcomes import handle_azampay_callback
from apps.payments.services import (
    MOBILE_MONEY_METHOD,
    available_payment_methods,
    azampay_amount,
    simulator_enabled,
)

logger = logging.getLogger(__name__)


class AzamPayCallbackView(APIView):
    """`POST /api/payments/azampay/callback/<token>`: AzamPay's MNO checkout result. AzamPay
    doesn't sign callbacks, so the secret path token is what keeps forged results out; the
    handler additionally requires the reference and amount to match a pending payment."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, token):
        if not hmac.compare_digest(token, settings.AZAMPAY_CALLBACK_TOKEN):
            raise Http404
        outcome = handle_azampay_callback(request.data)
        logger.info("AzamPay callback %s: %s", request.data.get("utilityref"), outcome)
        # Always 200 once authenticated: a non-2xx only makes AzamPay retry the same payload.
        return Response({"success": True})


class PaymentMethodListView(APIView):
    """`GET /api/payments/methods`: what checkout offers (and, for Lipa Namba, the till to pay)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(available_payment_methods())


# --- Dev-only AzamPay sandbox simulator (PAYMENT_BACKEND=azampay_simulator) ------------------


class _SimulatorView(APIView):
    """Unauthenticated on purpose (it plays the customer's phone), so it only exists while the
    simulator backend is configured."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        if not simulator_enabled():
            raise Http404
        super().initial(request, *args, **kwargs)


def _pending_pushes():
    return PaymentRecord.objects.filter(
        method=MOBILE_MONEY_METHOD, status=PaymentRecord.Status.PENDING
    ).order_by("-created_at")


class SimulatorPushListView(_SimulatorView):
    def get(self, request):
        return Response(
            [
                {
                    "reference": record.transaction_reference,
                    "order_id": record.order_id,
                    "msisdn": record.masked_msisdn,
                    "provider": record.provider,
                    "amount": azampay_amount(record.amount),
                    "created_at": record.created_at,
                }
                for record in _pending_pushes()
            ]
        )


class SimulatorDecisionSerializer(serializers.Serializer):
    pin = serializers.RegexField(r"^\d{4}$", required=False)


class SimulatorPushDecisionView(_SimulatorView):
    """Approve or reject a pending push. Builds exactly the payload AzamPay would POST to our
    callback and runs it through the same handler, so the simulator exercises the real path."""

    approve = True

    def post(self, request, reference):
        record = get_object_or_404(_pending_pushes(), transaction_reference=reference)
        if self.approve:
            SimulatorDecisionSerializer(data=request.data).is_valid(raise_exception=True)
        payload = {
            "msisdn": record.msisdn,
            "amount": azampay_amount(record.amount),
            "message": "Payment successful" if self.approve else "Customer rejected the payment",
            "utilityref": record.transaction_reference,
            "operator": record.provider,
            "reference": record.provider_reference or f"SIM-{record.transaction_reference[:12]}",
            "transactionstatus": "success" if self.approve else "failure",
            "submerchantAcc": None,
            "fspReferenceId": f"FSP{record.id:08d}",
        }
        outcome = handle_azampay_callback(payload)
        return Response({"callback": payload, "outcome": outcome})
