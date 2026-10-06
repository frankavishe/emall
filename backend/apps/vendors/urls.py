from django.urls import path

from . import views

urlpatterns = [
    path("shops", views.VendorShopListCreateView.as_view(), name="vendor-shops"),
    path(
        "shops/<int:shop_id>/logo",
        views.VendorShopLogoView.as_view(),
        name="vendor-shop-logo",
    ),
]

admin_urlpatterns = [
    path("shops", views.AdminShopListView.as_view(), name="admin-shops"),
    path(
        "shops/<int:shop_id>/approve",
        views.AdminShopApproveView.as_view(),
        name="admin-shop-approve",
    ),
    path(
        "shops/<int:shop_id>/reject",
        views.AdminShopRejectView.as_view(),
        name="admin-shop-reject",
    ),
]
