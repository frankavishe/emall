import hmac
import logging

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import record
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import AdminArea
from apps.payments.models import PaymentRecord, RefundDue
from apps.payments.outcomes import handle_azampay_callback
from apps.payments.services import (
    MOBILE_MONEY_METHOD,
    available_payment_methods,
    azampay_amount,
    simulator_enabled,
)
from apps.realtime.broadcast import publish_on_commit
from apps.realtime.groups import ADMINS

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
                    # A booking's payment has no order; the phone page shows this instead.
                    "order_id": record.order_id,
                    "booking_id": record.booking_id,
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


# --- Administrator: money owed back ---------------------------------------------


class AdminRefundSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source="payment.booking_id", read_only=True)
    shop = serializers.CharField(source="payment.booking.shop.name", read_only=True)
    service = serializers.CharField(source="payment.booking.service.name", read_only=True)
    customer_name = serializers.CharField(source="payment.booking.contact_name", read_only=True)
    customer_email = serializers.CharField(source="payment.booking.contact_email", read_only=True)
    contact_phone = serializers.CharField(source="payment.booking.contact_phone", read_only=True)
    payment_method = serializers.CharField(source="payment.method", read_only=True)
    payment_msisdn = serializers.CharField(source="payment.msisdn", read_only=True)
    payment_reference = serializers.CharField(source="payment.provider_reference", read_only=True)
    paid_by_email = serializers.EmailField(source="paid_by.email", read_only=True, default=None)

    class Meta:
        model = RefundDue
        fields = [
            "id",
            "booking_id",
            "shop",
            "service",
            "customer_name",
            "customer_email",
            "contact_phone",
            "payment_method",
            "payment_msisdn",
            "payment_reference",
            "amount",
            "reason",
            "note",
            "status",
            "paid_reference",
            "paid_by_email",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class MarkRefundPaidSerializer(serializers.Serializer):
    paid_reference = serializers.CharField(max_length=128, trim_whitespace=True)


def _refund_rows():
    return RefundDue.objects.select_related(
        "payment__booking__shop",
        "payment__booking__service",
        "payment__booking__customer",
        "paid_by",
    )


class AdminRefundListView(ListAPIView):
    """`GET /api/admin/refunds?status=`: money owed back, oldest due first."""

    permission_classes = [AdminArea("finance")]
    serializer_class = AdminRefundSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = _refund_rows()
        wanted = self.request.query_params.get("status")
        if wanted:
            queryset = queryset.filter(status=wanted)
        # Due entries first, oldest at the top: that is the order they should be paid in.
        return queryset.order_by("-status", "created_at", "id")


class AdminRefundMarkPaidView(APIView):
    """`POST /api/admin/refunds/{id}/mark-paid`: the administrator sent the money by hand. Works
    once; a repeat is a 409 and changes nothing."""

    permission_classes = [AdminArea("finance")]

    def post(self, request, refund_id):
        serializer = MarkRefundPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            refund = get_object_or_404(RefundDue.objects.select_for_update(), pk=refund_id)
            if refund.status == RefundDue.Status.PAID:
                return Response(
                    {"detail": "This refund has already been paid."},
                    status=status.HTTP_409_CONFLICT,
                )
            refund.status = RefundDue.Status.PAID
            refund.paid_reference = serializer.validated_data["paid_reference"]
            refund.paid_by = request.user
            refund.paid_at = timezone.now()
            refund.save(update_fields=["status", "paid_reference", "paid_by", "paid_at"])
            record(
                AuditAction.REFUND_PAID,
                request=request,
                target=refund.payment.booking,
                metadata={
                    "refund_id": refund.id,
                    "amount": refund.amount,
                    "paid_reference": refund.paid_reference,
                },
            )
            publish_on_commit([ADMINS], {"type": "refund.updated", "refund_id": refund.id})
        return Response(AdminRefundSerializer(_refund_rows().get(pk=refund.pk)).data)
