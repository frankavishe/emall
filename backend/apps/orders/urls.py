from django.urls import path

from . import views

checkout_urlpatterns = [
    path("checkout", views.CheckoutView.as_view(), name="checkout"),
    path(
        "checkout/delivery-quote",
        views.DeliveryQuoteView.as_view(),
        name="checkout-delivery-quote",
    ),
]

urlpatterns = [
    path("orders", views.OrderListView.as_view(), name="order-list"),
    path("orders/<int:order_id>", views.OrderDetailView.as_view(), name="order-detail"),
    path(
        "orders/<int:order_id>/payment-status",
        views.OrderPaymentStatusView.as_view(),
        name="order-payment-status",
    ),
    path(
        "orders/track/<str:token>",
        views.GuestOrderDetailView.as_view(),
        name="guest-order-detail",
    ),
    path(
        "orders/track/<str:token>/payment-status",
        views.GuestOrderPaymentStatusView.as_view(),
        name="guest-order-payment-status",
    ),
]

vendor_urlpatterns = [
    path(
        "order-items",
        views.VendorOrderItemListView.as_view(),
        name="vendor-order-item-list",
    ),
    path(
        "order-items/<int:item_id>/status",
        views.VendorOrderItemStatusUpdateView.as_view(),
        name="vendor-order-item-status-update",
    ),
]

admin_urlpatterns = [
    path(
        "order-items",
        views.AdminOrderItemListView.as_view(),
        name="admin-order-item-list",
    ),
    path(
        "order-items/<int:item_id>/rider",
        views.AdminOrderItemAssignRiderView.as_view(),
        name="admin-order-item-assign-rider",
    ),
]
