from django.urls import path

from . import views

checkout_urlpatterns = [
    path("checkout", views.CheckoutView.as_view(), name="checkout"),
]

urlpatterns = [
    path("orders", views.OrderListView.as_view(), name="order-list"),
    path("orders/<int:order_id>", views.OrderDetailView.as_view(), name="order-detail"),
]
