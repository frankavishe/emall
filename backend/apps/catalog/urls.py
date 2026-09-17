from django.urls import path

from . import views

urlpatterns = [
    path("categories", views.CategoryListView.as_view(), name="catalog-categories"),
]

vendor_urlpatterns = [
    path("products", views.VendorProductListCreateView.as_view(), name="vendor-products"),
    path(
        "products/<int:product_id>",
        views.VendorProductDetailView.as_view(),
        name="vendor-product-detail",
    ),
    path(
        "products/<int:product_id>/publish",
        views.VendorProductPublishView.as_view(),
        name="vendor-product-publish",
    ),
    path(
        "products/<int:product_id>/unpublish",
        views.VendorProductUnpublishView.as_view(),
        name="vendor-product-unpublish",
    ),
]
