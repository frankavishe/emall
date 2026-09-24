from django.urls import path

from . import views

urlpatterns = [
    path(
        "feedback/products/<int:product_id>/review",
        views.CustomerReviewView.as_view(),
        name="feedback-review",
    ),
]

vendor_urlpatterns = [
    path("reviews", views.VendorReviewListView.as_view(), name="vendor-review-list"),
]
