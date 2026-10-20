from django.urls import path

from . import reports, views

admin_urlpatterns = [
    path(
        "finance/settings", views.AdminFinanceSettingsView.as_view(), name="admin-finance-settings"
    ),
    path("finance/summary", views.AdminFinanceSummaryView.as_view(), name="admin-finance-summary"),
    path(
        "finance/balances", views.AdminShopBalanceListView.as_view(), name="admin-finance-balances"
    ),
    path(
        "finance/report.pdf", reports.AdminFinanceReportView.as_view(), name="admin-finance-report"
    ),
    path("shops/<int:shop_id>", views.AdminShopDetailView.as_view(), name="admin-shop-detail"),
    path(
        "shops/<int:shop_id>/commission",
        views.AdminShopCommissionView.as_view(),
        name="admin-shop-commission",
    ),
    path(
        "shops/<int:shop_id>/payouts",
        views.AdminShopPayoutCreateView.as_view(),
        name="admin-shop-payout-create",
    ),
    path("payouts", views.AdminPayoutListView.as_view(), name="admin-payout-list"),
    path("payouts/report.pdf", reports.AdminPayoutReportView.as_view(), name="admin-payout-report"),
    path(
        "payouts/<int:payout_id>", views.AdminPayoutDetailView.as_view(), name="admin-payout-detail"
    ),
    path(
        "payouts/<int:payout_id>/retry",
        views.AdminPayoutRetryView.as_view(),
        name="admin-payout-retry",
    ),
    path(
        "payouts/<int:payout_id>/report.pdf",
        reports.AdminPayoutStatementView.as_view(),
        name="admin-payout-statement",
    ),
    path("transactions", views.AdminTransactionListView.as_view(), name="admin-transactions"),
    path(
        "transactions/report.pdf",
        reports.AdminTransactionReportView.as_view(),
        name="admin-transactions-report",
    ),
    path("orders/<int:order_id>", views.AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path(
        "orders/<int:order_id>/payment/confirm",
        views.AdminOrderPaymentSettleView.as_view(confirm=True),
        name="admin-order-payment-confirm",
    ),
    path(
        "orders/<int:order_id>/payment/reject",
        views.AdminOrderPaymentSettleView.as_view(confirm=False),
        name="admin-order-payment-reject",
    ),
    path("products", views.AdminProductListView.as_view(), name="admin-products"),
]

vendor_urlpatterns = [
    path(
        "shops/<int:shop_id>/payout-details",
        views.VendorPayoutDetailsView.as_view(),
        name="vendor-shop-payout-details",
    ),
    path("earnings", views.VendorEarningsView.as_view(), name="vendor-earnings"),
    path(
        "earnings/report.pdf",
        reports.VendorEarningsReportView.as_view(),
        name="vendor-earnings-report",
    ),
    path("payouts", views.VendorPayoutListView.as_view(), name="vendor-payouts"),
]
