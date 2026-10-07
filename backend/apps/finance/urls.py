from django.urls import path

from . import views

admin_urlpatterns = [
    path(
        "finance/settings", views.AdminFinanceSettingsView.as_view(), name="admin-finance-settings"
    ),
    path("finance/summary", views.AdminFinanceSummaryView.as_view(), name="admin-finance-summary"),
    path(
        "finance/balances", views.AdminShopBalanceListView.as_view(), name="admin-finance-balances"
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
    path(
        "payouts/<int:payout_id>", views.AdminPayoutDetailView.as_view(), name="admin-payout-detail"
    ),
    path(
        "payouts/<int:payout_id>/retry",
        views.AdminPayoutRetryView.as_view(),
        name="admin-payout-retry",
    ),
    path("transactions", views.AdminTransactionListView.as_view(), name="admin-transactions"),
    path("orders/<int:order_id>", views.AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("products", views.AdminProductListView.as_view(), name="admin-products"),
]

vendor_urlpatterns = [
    path(
        "shops/<int:shop_id>/payout-details",
        views.VendorPayoutDetailsView.as_view(),
        name="vendor-shop-payout-details",
    ),
    path("earnings", views.VendorEarningsView.as_view(), name="vendor-earnings"),
    path("payouts", views.VendorPayoutListView.as_view(), name="vendor-payouts"),
]
