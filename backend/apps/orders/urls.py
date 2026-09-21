from django.urls import path

from . import views

checkout_urlpatterns = [
    path("checkout", views.CheckoutView.as_view(), name="checkout"),
]

urlpatterns = [
    path("orders", views.OrderListView.as_view(), name="order-list"),
    path("orders/<int:order_id>", views.OrderDetailView.as_view(), name="order-detail"),
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
