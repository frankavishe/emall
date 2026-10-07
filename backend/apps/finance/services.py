"""Mall money logic: the commission split frozen at checkout, payouts to shop owners, and the
balance/summary figures shown to Administrators and Vendors.

Money flow: the customer pays the mall the line `subtotal`; the mall keeps `commission_amount`
and owes the shop `vendor_earning`. An earning is
- pending   while the line is PENDING / PROCESSING / SHIPPED,
- available once the line is DELIVERED and not yet in a payout,
- in payout while its payout is PENDING / PROCESSING,
- paid      once its payout SUCCEEDED.
Cancelled lines never pay out.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.finance import disbursement
from apps.finance.models import Payout, PlatformSettings
from apps.orders.models import OrderItem
from apps.vendors.models import Shop

logger = logging.getLogger(__name__)

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class FinanceError(Exception):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(detail)


def split_line(subtotal, rate):
    """Returns `(commission_amount, vendor_earning)` for a line `subtotal` at `rate` percent."""

    commission = (Decimal(subtotal) * Decimal(rate) / Decimal("100")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    return commission, Decimal(subtotal) - commission


def _validate_rate(rate):
    rate = Decimal(rate)
    if rate < 0 or rate > 100:
        raise FinanceError("Commission rate must be between 0 and 100.")
    return rate.quantize(CENT)


def set_default_commission_rate(*, rate, admin):
    platform = PlatformSettings.get_solo()
    platform.default_commission_rate = _validate_rate(rate)
    platform.updated_by = admin
    platform.save(update_fields=["default_commission_rate", "updated_by", "updated_at"])
    return platform


def set_shop_commission_rate(*, shop, rate):
    """`rate=None` clears the override so the shop uses the mall default again. Only affects
    future checkouts — existing lines keep the rate frozen on them."""

    shop.commission_rate = None if rate is None else _validate_rate(rate)
    shop.save(update_fields=["commission_rate"])
    return shop


# --- Payouts -----------------------------------------------------------------


def _available_lines(shop):
    return OrderItem.objects.filter(
        product__shop=shop, status=OrderItem.Status.DELIVERED, payout__isnull=True
    )


def _claim_lines(payout, shop):
    """Locks the shop's available lines and attaches them to `payout`. Caller holds a
    transaction and the shop row lock."""

    lines = list(_available_lines(shop).select_for_update(of=("self",)).order_by("id"))
    if not lines:
        raise FinanceError("This shop has no delivered earnings waiting to be paid out.")
    amount = sum((line.vendor_earning for line in lines), ZERO)
    if amount <= 0:
        raise FinanceError("This shop's available balance is zero.")
    OrderItem.objects.filter(id__in=[line.id for line in lines]).update(payout=payout)
    return amount


def _snapshot_destination(payout, shop):
    if not shop.has_payout_details:
        raise FinanceError("The shop owner hasn't set up their mobile-money payout details yet.")
    payout.network = shop.payout_network
    payout.phone = shop.payout_phone
    payout.account_name = shop.payout_account_name


def _disburse(payout):
    """Calls the provider outside any transaction (no row locks held across the network call),
    then records the outcome. A FAILED payout releases its lines so they're available again."""

    try:
        result = disbursement.get_disbursement_service().disburse(
            amount=payout.amount,
            network=payout.network,
            phone=payout.phone,
            account_name=payout.account_name,
            reference=payout.reference,
        )
    except Exception as error:
        # Real adapters must return PROCESSING (not raise) when the outcome is unknown, so a
        # crash here really means nothing was sent.
        logger.exception("Disbursement failed for payout_id=%s", payout.id)
        result = disbursement.DisbursementResult(
            status=disbursement.FAILED, failure_reason=f"Provider error: {error}"
        )

    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(pk=payout.pk)
        payout.provider_reference = result.provider_reference
        payout.failure_reason = result.failure_reason
        if result.status == disbursement.SUCCEEDED:
            payout.status = Payout.Status.SUCCEEDED
            payout.completed_at = timezone.now()
        elif result.status == disbursement.PROCESSING:
            payout.status = Payout.Status.PROCESSING
        else:
            payout.status = Payout.Status.FAILED
            payout.completed_at = timezone.now()
            OrderItem.objects.filter(payout=payout).update(payout=None)
        payout.save()
    return payout


def create_payout(*, shop, admin):
    """Pays out everything the shop has available right now."""

    with transaction.atomic():
        shop = Shop.objects.select_for_update().get(pk=shop.pk)
        payout = Payout(shop=shop, amount=ZERO, created_by=admin)
        _snapshot_destination(payout, shop)
        payout.save()
        payout.amount = _claim_lines(payout, shop)
        payout.save(update_fields=["amount"])
    return _disburse(payout)


def retry_payout(*, payout):
    """Re-attempts a FAILED payout with the shop's current payout details and whatever is
    available for the shop now."""

    with transaction.atomic():
        shop = Shop.objects.select_for_update().get(pk=payout.shop_id)
        payout = Payout.objects.select_for_update().get(pk=payout.pk)
        if payout.status != Payout.Status.FAILED:
            raise FinanceError("Only a failed payout can be retried.")
        _snapshot_destination(payout, shop)
        payout.amount = _claim_lines(payout, shop)
        payout.status = Payout.Status.PENDING
        payout.provider_reference = None
        payout.failure_reason = ""
        payout.completed_at = None
        payout.save()
    return _disburse(payout)


# --- Figures -------------------------------------------------------------------

_MONEY = DecimalField(max_digits=14, decimal_places=2)
_IN_PROGRESS = [
    OrderItem.Status.PENDING,
    OrderItem.Status.PROCESSING,
    OrderItem.Status.SHIPPED,
]
_PAYOUT_OPEN = [Payout.Status.PENDING, Payout.Status.PROCESSING]


def _sum(expression, condition=None):
    return Coalesce(
        Sum(expression, filter=condition, output_field=_MONEY),
        Value(ZERO),
        output_field=_MONEY,
    )


def balance_aggregates(prefix=""):
    """Aggregate expressions over order lines reached via `prefix` (`""` from `OrderItem`,
    `"products__order_items__"` from `Shop`)."""

    def f(name):
        return F(f"{prefix}{name}")

    def q(**lookups):
        return Q(**{f"{prefix}{key}": value for key, value in lookups.items()})

    not_cancelled = ~q(status=OrderItem.Status.CANCELLED)
    delivered = q(status=OrderItem.Status.DELIVERED)
    return {
        "gross_sales": _sum(f("unit_price") * f("quantity"), not_cancelled),
        "commission_earned": _sum(f("commission_amount"), delivered),
        "commission_pending": _sum(f("commission_amount"), q(status__in=_IN_PROGRESS)),
        "pending_earnings": _sum(f("vendor_earning"), q(status__in=_IN_PROGRESS)),
        "available_balance": _sum(f("vendor_earning"), delivered & q(payout__isnull=True)),
        "in_payout": _sum(f("vendor_earning"), delivered & q(payout__status__in=_PAYOUT_OPEN)),
        "paid_out": _sum(f("vendor_earning"), q(payout__status=Payout.Status.SUCCEEDED)),
    }


def _date_filtered_lines(date_from=None, date_to=None):
    lines = OrderItem.objects.all()
    if date_from:
        lines = lines.filter(order__placed_at__date__gte=date_from)
    if date_to:
        lines = lines.filter(order__placed_at__date__lte=date_to)
    return lines


def platform_summary(*, date_from=None, date_to=None):
    """Mall-wide figures for orders placed in the (inclusive) date range."""

    lines = _date_filtered_lines(date_from, date_to)
    figures = lines.aggregate(
        **balance_aggregates(),
        order_count=Count("order", distinct=True),
        line_count=Count("id"),
    )
    figures["default_commission_rate"] = PlatformSettings.get_solo().default_commission_rate
    return figures


def shops_with_balances():
    """Every shop annotated with its balance figures (one query)."""

    return (
        Shop.objects.select_related("owner")
        .annotate(**balance_aggregates("products__order_items__"))
        .order_by("-available_balance", "name")
    )


def shop_balance(shop):
    figures = OrderItem.objects.filter(product__shop=shop).aggregate(**balance_aggregates())
    figures["commission_rate"] = shop.effective_commission_rate()
    figures["commission_rate_is_override"] = shop.commission_rate is not None
    return figures
