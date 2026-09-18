from django.urls import path

from . import views

urlpatterns = [
    path("cart", views.CartDetailView.as_view(), name="cart-detail"),
    path("cart/items", views.CartItemCreateView.as_view(), name="cart-item-create"),
    path(
        "cart/items/<int:item_id>",
        views.CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),
]
