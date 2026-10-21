from django.db.models import Count, DecimalField, F, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import changed_fields, record
from apps.catalog.models import Product
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import AdminArea, IsCustomer, IsVendor
from apps.finance.models import Payout, PlatformSettings
from apps.finance.serializers import (
    AdminOrderDetailSerializer,
    AdminProductSerializer,
    AdminShopBalanceSerializer,
    AdminShopDetailSerializer,
    AdminTransactionSerializer,
    DateRangeSerializer,
    PayoutDetailSerializer,
    PayoutDetailsSerializer,
    PayoutSerializer,
    PlatformSettingsSerializer,
    PlatformSummarySerializer,
    SettlePaymentSerializer,
    ShopCommissionSerializer,
    VendorShopEarningsSerializer,
)
from apps.finance.services import (
    FinanceError,
    create_payout,
    filter_transactions,
    payout_queryset,
    platform_summary,
    retry_payout,
    set_shop_commission_rate,
    shop_balance,
    shops_with_balances,
    update_platform_settings,
    vendor_shop_earnings,
)
from apps.orders.models import Order, OrderItem
from apps.payments.outcomes import SettlementError, settle_manual_payment
from apps.vendors.models import Shop

_MONEY = DecimalField(max_digits=14, decimal_places=2)


def _int_param(request, name):
    """An integer query param, or None when absent or not a number."""
    value = request.query_params.get(name, "")
    return int(value) if value.isdigit() else None


def _error(error):
    return Response({"detail": error.detail}, status=status.HTTP_400_BAD_REQUEST)


def _date_range(request):
    serializer = DateRangeSerializer(
        data={
            key: value
            for key, value in (
                ("date_from", request.query_params.get("from")),
                ("date_to", request.query_params.get("to")),
            )
            if value
        }
    )
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# --- Administrator -----------------------------------------------------------------


class AdminFinanceSettingsView(APIView):
    permission_classes = [AdminArea("finance")]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.get_solo()).data)

    def patch(self, request):
        serializer = PlatformSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        before = PlatformSettings.get_solo()
        changes = {
            name: {"from": getattr(before, name), "to": value}
            for name, value in data.items()
            if getattr(before, name) != value
        }
        platform = update_platform_settings(admin=request.user, **data)
        if changes:
            record(
                AuditAction.SETTINGS_UPDATED,
                request=request,
                target=platform,
                target_repr="Platform settings",
                metadata={"changes": changes},
            )
        return Response(PlatformSettingsSerializer(platform).data)


class AdminFinanceSummaryView(APIView):
    """Mall-wide money figures; `?from=YYYY-MM-DD&to=YYYY-MM-DD` limits to orders placed then."""

    permission_classes = [AdminArea("finance")]

    def get(self, request):
        figures = platform_summary(**_date_range(request))
        return Response(PlatformSummarySerializer(figures).data)


class AdminShopBalanceListView(ListAPIView):
    permission_classes = [AdminArea("finance")]
    serializer_class = AdminShopBalanceSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = shops_with_balances()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["default_commission_rate"] = PlatformSettings.get_solo().default_commission_rate
        return context


class AdminShopDetailView(APIView):
    permission_classes = [AdminArea("shops")]

    def get(self, request, shop_id):
        shop = get_object_or_404(
            Shop.objects.select_related("owner").annotate(
                product_count=Count("products", filter=Q(products__is_deleted=False)),
                published_product_count=Count(
                    "products",
                    filter=Q(products__is_deleted=False, products__is_published=True),
                ),
            ),
            pk=shop_id,
        )
        serializer = AdminShopDetailSerializer(
            shop, context={"request": request, "balance": shop_balance(shop)}
        )
        return Response(serializer.data)


class AdminShopCommissionView(APIView):
    """Sets (or with `null`, clears) a shop's commission override. Applies to future orders."""

    permission_classes = [AdminArea("finance")]

    def patch(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id)
        serializer = ShopCommissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_rate = shop.commission_rate
        try:
            set_shop_commission_rate(shop=shop, rate=serializer.validated_data["commission_rate"])
        except FinanceError as error:
            return _error(error)
        record(
            AuditAction.SHOP_COMMISSION_SET,
            request=request,
            target=shop,
            metadata={"from": previous_rate, "to": shop.commission_rate},
        )
        return Response(
            {
                "id": shop.id,
                "commission_rate": shop.commission_rate,
                "effective_commission_rate": shop.effective_commission_rate(),
            }
        )


class AdminShopPayoutCreateView(APIView):
    """Sends the shop everything it has available (delivered, not yet paid)."""

    permission_classes = [AdminArea("finance")]

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id)
        try:
            payout = create_payout(shop=shop, admin=request.user)
        except FinanceError as error:
            return _error(error)
        _record_payout(request, AuditAction.PAYOUT_CREATED, payout, shop)
        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


def _record_payout(request, action, payout, shop):
    record(
        action,
        request=request,
        target=payout,
        target_repr=f"Payout #{payout.pk} · {shop.name}",
        metadata={"shop_id": shop.pk, "amount": payout.amount, "status": payout.status},
    )


def _admin_payouts(request):
    return payout_queryset(
        shop_id=_int_param(request, "shop"), status=request.query_params.get("status")
    )


def _payout_with_lines(payout_id):
    return get_object_or_404(
        payout_queryset().prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related("product").order_by("id"),
            )
        ),
        pk=payout_id,
    )


class AdminPayoutListView(ListAPIView):
    permission_classes = [AdminArea("finance")]
    serializer_class = PayoutSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        return _admin_payouts(self.request)


class AdminPayoutDetailView(APIView):
    permission_classes = [AdminArea("finance")]

    def get(self, request, payout_id):
        return Response(PayoutDetailSerializer(_payout_with_lines(payout_id)).data)


class AdminPayoutRetryView(APIView):
    permission_classes = [AdminArea("finance")]

    def post(self, request, payout_id):
        payout = get_object_or_404(Payout.objects.select_related("shop"), pk=payout_id)
        try:
            payout = retry_payout(payout=payout)
        except FinanceError as error:
            return _error(error)
        _record_payout(request, AuditAction.PAYOUT_RETRIED, payout, payout.shop)
        return Response(PayoutSerializer(payout).data)


class AdminTransactionListView(ListAPIView):
    """Every customer payment the mall has received, newest first. Filters: `from`, `to`
    (dates), `search` (order id, payment reference, customer name/email)."""

    permission_classes = [AdminArea("finance")]
    serializer_class = AdminTransactionSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        return _admin_transactions(self.request)


def _admin_transactions(request):
    params = request.query_params
    return filter_transactions(
        **_date_range(request),
        status=params.get("status"),
        method=params.get("method"),
        search=params.get("search"),
    )


class AdminOrderDetailView(APIView):
    permission_classes = [AdminArea("orders")]

    def get(self, request, order_id):
        return Response(_admin_order_data(order_id))


def _admin_order_data(order_id):
    order = get_object_or_404(
        Order.objects.select_related("customer", "payment__settled_by").prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related("product__shop", "payout").order_by("id"),
            )
        ),
        pk=order_id,
    )
    return AdminOrderDetailSerializer(order).data


class AdminOrderPaymentSettleView(APIView):
    """`POST /api/admin/orders/{id}/payment/confirm` (or `/reject`, with an optional `reason`):
    an administrator settling a cash-on-delivery or Lipa Namba payment by hand."""

    permission_classes = [AdminArea("orders", write_permission="finance.manage")]
    confirm = True

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        serializer = SettlePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")
        try:
            settle_manual_payment(
                order=order, admin=request.user, confirm=self.confirm, reason=reason
            )
        except SettlementError as error:
            return _error(error)
        record(
            AuditAction.PAYMENT_CONFIRMED if self.confirm else AuditAction.PAYMENT_REJECTED,
            request=request,
            target=order,
            target_repr=f"Order #{order.pk}",
            metadata={"reason": reason} if reason else {},
        )
        return Response(_admin_order_data(order_id))


class AdminProductListView(ListAPIView):
    """Every product in the mall, including drafts and deleted ones. Filters: `shop`, `search`,
    `published` (true/false), `deleted` (true/false)."""

    permission_classes = [AdminArea("catalog")]
    serializer_class = AdminProductSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        sold = ~Q(order_items__status=OrderItem.Status.CANCELLED) & Q(
            order_items__order__status=Order.Status.PLACED
        )
        queryset = (
            Product.all_objects.select_related("shop", "category")
            .annotate(
                units_sold=Coalesce(Sum("order_items__quantity", filter=sold), Value(0)),
                revenue=Coalesce(
                    Sum(
                        F("order_items__unit_price") * F("order_items__quantity"),
                        filter=sold,
                        output_field=_MONEY,
                    ),
                    Value(0),
                    output_field=_MONEY,
                ),
            )
            .order_by("-created_at")
        )
        params = self.request.query_params
        shop = _int_param(self.request, "shop")
        if shop is not None:
            queryset = queryset.filter(shop_id=shop)
        if params.get("search"):
            queryset = queryset.filter(name__icontains=params["search"].strip())
        for param, field in (("published", "is_published"), ("deleted", "is_deleted")):
            value = params.get(param)
            if value in ("true", "false"):
                queryset = queryset.filter(**{field: value == "true"})
        return queryset


# --- Vendor --------------------------------------------------------------------------


class VendorPayoutDetailsView(APIView):
    """Where the mall sends this shop's earnings. Ownership only, any approval status (like the
    shop's logo/theme)."""

    permission_classes = [IsCustomer]

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        return Response(PayoutDetailsSerializer(shop).data)

    def patch(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, owner=request.user)
        serializer = PayoutDetailsSerializer(shop, data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = changed_fields(shop, serializer.validated_data)
        serializer.save()
        # Field names only: account numbers stay out of the audit trail.
        if fields:
            record(
                AuditAction.PAYOUT_DETAILS_UPDATED,
                request=request,
                actor_role="VENDOR",
                target=shop,
                metadata={"fields": fields},
            )
        return Response(serializer.data)


class VendorEarningsView(APIView):
    """Balance figures for each of the requester's shops (`?shop=<id>` for just one). The
    per-line breakdown is on `GET /api/vendor/order-items`."""

    permission_classes = [IsVendor]

    def get(self, request):
        rows = vendor_shop_earnings(request.user, _int_param(request, "shop"))
        return Response(VendorShopEarningsSerializer(rows, many=True).data)


def _vendor_payouts(request):
    return payout_queryset(shop_id=_int_param(request, "shop")).filter(shop__owner=request.user)


class VendorPayoutListView(ListAPIView):
    permission_classes = [IsVendor]
    serializer_class = PayoutSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        return _vendor_payouts(self.request)
