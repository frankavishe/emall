from django.urls import path

from . import views

admin_urlpatterns = [
    path("riders", views.AdminRiderListCreateView.as_view(), name="admin-riders"),
    path("riders/<int:rider_id>", views.AdminRiderDetailView.as_view(), name="admin-rider"),
]

rider_urlpatterns = [
    path("deliveries", views.RiderDeliveryListView.as_view(), name="rider-deliveries"),
    path(
        "deliveries/<int:item_id>/status",
        views.RiderDeliveryStatusView.as_view(),
        name="rider-delivery-status",
    ),
]
