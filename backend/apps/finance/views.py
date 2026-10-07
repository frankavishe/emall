from django.db.models import Count, DecimalField, F, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsAdministrator, IsCustomer, IsVendor
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
    ShopCommissionSerializer,
    VendorShopEarningsSerializer,
)
from apps.finance.services import (
    FinanceError,
    balance_aggregates,
    create_payout,
    platform_summary,
    retry_payout,
    set_default_commission_rate,
    set_shop_commission_rate,
    shop_balance,
    shops_with_balances,
)
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentRecord
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
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.get_solo()).data)

    def patch(self, request):
        serializer = PlatformSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        platform = set_default_commission_rate(
            rate=serializer.validated_data["default_commission_rate"], admin=request.user
        )
        return Response(PlatformSettingsSerializer(platform).data)


class AdminFinanceSummaryView(APIView):
    """Mall-wide money figures; `?from=YYYY-MM-DD&to=YYYY-MM-DD` limits to orders placed then."""

    permission_classes = [IsAdministrator]

    def get(self, request):
        figures = platform_summary(**_date_range(request))
        return Response(PlatformSummarySerializer(figures).data)


class AdminShopBalanceListView(ListAPIView):
    permission_classes = [IsAdministrator]
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
    permission_classes = [IsAdministrator]

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

    permission_classes = [IsAdministrator]

    def patch(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id)
        serializer = ShopCommissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            set_shop_commission_rate(shop=shop, rate=serializer.validated_data["commission_rate"])
        except FinanceError as error:
            return _error(error)
        return Response(
            {
                "id": shop.id,
                "commission_rate": shop.commission_rate,
                "effective_commission_rate": shop.effective_commission_rate(),
            }
        )


class AdminShopPayoutCreateView(APIView):
    """Sends the shop everything it has available (delivered, not yet paid)."""

    permission_classes = [IsAdministrator]

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id)
        try:
            payout = create_payout(shop=shop, admin=request.user)
        except FinanceError as error:
            return _error(error)
        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


def _payout_queryset():
    return (
        Payout.objects.select_related("shop", "created_by")
        .annotate(line_count=Count("items"))
        .order_by("-created_at")
    )


class AdminPayoutListView(ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = PayoutSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = _payout_queryset()
        shop = _int_param(self.request, "shop")
        if shop is not None:
            queryset = queryset.filter(shop_id=shop)
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset


class AdminPayoutDetailView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request, payout_id):
        payout = get_object_or_404(
            _payout_queryset().prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product").order_by("id"),
                )
            ),
            pk=payout_id,
        )
        return Response(PayoutDetailSerializer(payout).data)


class AdminPayoutRetryView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, payout_id):
        payout = get_object_or_404(Payout, pk=payout_id)
        try:
            payout = retry_payout(payout=payout)
        except FinanceError as error:
            return _error(error)
        return Response(PayoutSerializer(payout).data)


class AdminTransactionListView(ListAPIView):
    """Every customer payment the mall has received, newest first. Filters: `from`, `to`
    (dates), `search` (order id, payment reference, customer name/email)."""

    permission_classes = [IsAdministrator]
    serializer_class = AdminTransactionSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = (
            PaymentRecord.objects.select_related("order__customer")
            .annotate(
                commission_total=Coalesce(
                    Sum("order__items__commission_amount", output_field=_MONEY),
                    Value(0),
                    output_field=_MONEY,
                ),
                shop_count=Count("order__items__product__shop", distinct=True),
            )
            .order_by("-created_at")
        )
        dates = _date_range(self.request)
        if dates.get("date_from"):
            queryset = queryset.filter(created_at__date__gte=dates["date_from"])
        if dates.get("date_to"):
            queryset = queryset.filter(created_at__date__lte=dates["date_to"])
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            condition = (
                Q(transaction_reference__icontains=search)
                | Q(order__customer__email__icontains=search)
                | Q(order__customer__name__icontains=search)
            )
            if search.isdigit():
                condition |= Q(order_id=int(search))
            queryset = queryset.filter(condition)
        return queryset


class AdminOrderDetailView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("customer", "payment").prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product__shop", "payout").order_by(
                        "id"
                    ),
                )
            ),
            pk=order_id,
        )
        return Response(AdminOrderDetailSerializer(order).data)


class AdminProductListView(ListAPIView):
    """Every product in the mall, including drafts and deleted ones. Filters: `shop`, `search`,
    `published` (true/false), `deleted` (true/false)."""

    permission_classes = [IsAdministrator]
    serializer_class = AdminProductSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        sold = ~Q(order_items__status=OrderItem.Status.CANCELLED)
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
        serializer.save()
        return Response(serializer.data)


class VendorEarningsView(APIView):
    """Balance figures for each of the requester's shops (`?shop=<id>` for just one). The
    per-line breakdown is on `GET /api/vendor/order-items`."""

    permission_classes = [IsVendor]

    def get(self, request):
        shops = Shop.objects.filter(owner=request.user).order_by("name")
        shop_param = _int_param(request, "shop")
        if shop_param is not None:
            shops = shops.filter(pk=shop_param)
        default_rate = PlatformSettings.get_solo().default_commission_rate
        aggregates = balance_aggregates("products__order_items__")
        rows = []
        for shop in shops.annotate(**aggregates):
            rows.append(
                {
                    "shop_id": shop.id,
                    "shop_name": shop.name,
                    "commission_rate": shop.commission_rate
                    if shop.commission_rate is not None
                    else default_rate,
                    "has_payout_details": shop.has_payout_details,
                    "payout_network": shop.payout_network,
                    "payout_phone": shop.payout_phone,
                    "payout_account_name": shop.payout_account_name,
                    **{key: getattr(shop, key) for key in aggregates},
                }
            )
        return Response(VendorShopEarningsSerializer(rows, many=True).data)


class VendorPayoutListView(ListAPIView):
    permission_classes = [IsVendor]
    serializer_class = PayoutSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = _payout_queryset().filter(shop__owner=self.request.user)
        shop = _int_param(self.request, "shop")
        if shop is not None:
            queryset = queryset.filter(shop_id=shop)
        return queryset
