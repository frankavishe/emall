"""Printable PDF versions of the finance pages. Each report uses the same querysets as its JSON
endpoint, but lists every matching row instead of one page (up to `REPORT_ROW_LIMIT`)."""

from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.views import APIView
from xhtml2pdf import pisa

from apps.core.permissions import IsAdministrator, IsVendor
from apps.finance.models import Payout, PlatformSettings
from apps.finance.services import platform_summary, shops_with_balances, vendor_shop_earnings
from apps.finance.views import (
    _admin_payouts,
    _admin_transactions,
    _date_range,
    _payout_with_lines,
    _vendor_payouts,
)
from apps.payments.models import PaymentRecord
from apps.vendors.models import Shop

# Rows past this are left out (with a notice) so one request can't build a huge PDF.
REPORT_ROW_LIMIT = 5000

PAYMENT_METHOD_LABELS = {
    "card": "Card",
    "mobile_money": "Mobile money",
    "cod": "Cash on delivery",
    "lipa_namba": "Lipa Namba",
}


class ReportError(Exception):
    pass


def render_pdf(template, context, filename):
    html = render_to_string(
        template, {"printed_at": timezone.localtime(), "row_limit": REPORT_ROW_LIMIT, **context}
    )
    buffer = BytesIO()
    if pisa.CreatePDF(html, dest=buffer, encoding="utf-8").err:
        raise ReportError(f"Could not render {template}")
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _limited(queryset):
    """The first `REPORT_ROW_LIMIT` rows, and whether more were left out."""

    rows = list(queryset[: REPORT_ROW_LIMIT + 1])
    return rows[:REPORT_ROW_LIMIT], len(rows) > REPORT_ROW_LIMIT


def _filename(name):
    return f"mangimall-{name}-{timezone.localdate():%Y-%m-%d}.pdf"


def _date_filters(dates):
    if not dates:
        return [("Period", "All time")]
    start = dates.get("date_from")
    end = dates.get("date_to")
    return [("Period", f"{start or 'beginning'} to {end or 'today'}")]


class AdminFinanceReportView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        dates = _date_range(request)
        default_rate = PlatformSettings.get_solo().default_commission_rate
        shops, truncated = _limited(shops_with_balances())
        for shop in shops:
            shop.effective_rate = (
                shop.commission_rate if shop.commission_rate is not None else default_rate
            )
        return render_pdf(
            "finance/reports/finance.html",
            {
                "title": "Finance summary",
                "filters": _date_filters(dates),
                "figures": platform_summary(**dates),
                "shops": shops,
                "truncated": truncated,
            },
            _filename("finance"),
        )


class AdminTransactionReportView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        queryset = _admin_transactions(request)
        transactions, truncated = _limited(queryset)
        for tx in transactions:
            tx.method_label = PAYMENT_METHOD_LABELS.get(tx.method, tx.method.replace("_", " "))
        params = request.query_params
        filters = _date_filters(_date_range(request))
        if params.get("status") in PaymentRecord.Status.values:
            filters.append(("Status", PaymentRecord.Status(params["status"]).label))
        method = params.get("method")
        if method:
            filters.append(("Method", PAYMENT_METHOD_LABELS.get(method, method)))
        if (params.get("search") or "").strip():
            filters.append(("Search", params["search"].strip()))
        return render_pdf(
            "finance/reports/transactions.html",
            {
                "title": "Transactions",
                "filters": filters,
                "transactions": transactions,
                "truncated": truncated,
                "total_amount": sum(tx.amount for tx in transactions),
                "total_commission": sum(tx.commission_total for tx in transactions),
            },
            _filename("transactions"),
        )


def _payout_filters(request, shops):
    filters = []
    shop_id = request.query_params.get("shop", "")
    if shop_id.isdigit():
        shop = shops.filter(pk=int(shop_id)).first()
        filters.append(("Shop", shop.name if shop else "Unknown shop"))
    status = request.query_params.get("status")
    if status in Payout.Status.values:
        filters.append(("Status", Payout.Status(status).label))
    return filters


class AdminPayoutReportView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        payouts, truncated = _limited(_admin_payouts(request))
        return render_pdf(
            "finance/reports/payouts.html",
            {
                "title": "Payouts",
                "filters": _payout_filters(request, Shop.objects.all()),
                "payouts": payouts,
                "truncated": truncated,
                "total_amount": sum(payout.amount for payout in payouts),
            },
            _filename("payouts"),
        )


class AdminPayoutStatementView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request, payout_id):
        payout = _payout_with_lines(payout_id)
        return render_pdf(
            "finance/reports/payout_statement.html",
            {"title": f"Payout {payout.reference}", "filters": [], "payout": payout},
            _filename(f"payout-{payout.reference}"),
        )


class VendorEarningsReportView(APIView):
    permission_classes = [IsVendor]

    def get(self, request):
        own_shops = Shop.objects.filter(owner=request.user)
        shop_param = request.query_params.get("shop", "")
        shops = vendor_shop_earnings(
            request.user, int(shop_param) if shop_param.isdigit() else None
        )
        payouts, truncated = _limited(_vendor_payouts(request))
        return render_pdf(
            "finance/reports/earnings.html",
            {
                "title": "Earnings",
                "filters": _payout_filters(request, own_shops),
                "shops": shops,
                "payouts": payouts,
                "truncated": truncated,
            },
            _filename("earnings"),
        )
