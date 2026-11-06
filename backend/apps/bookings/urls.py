from django.urls import path

from . import views

catalog_urlpatterns = [
    path("services", views.CatalogServiceListView.as_view(), name="catalog-services"),
    path(
        "services/<int:service_id>",
        views.CatalogServiceDetailView.as_view(),
        name="catalog-service-detail",
    ),
    path(
        "services/<int:service_id>/slots",
        views.CatalogServiceSlotsView.as_view(),
        name="catalog-service-slots",
    ),
]

vendor_urlpatterns = [
    path("services", views.VendorServiceListCreateView.as_view(), name="vendor-services"),
    path(
        "services/<int:service_id>",
        views.VendorServiceDetailView.as_view(),
        name="vendor-service-detail",
    ),
    path(
        "services/<int:service_id>/publish",
        views.VendorServicePublishView.as_view(),
        name="vendor-service-publish",
    ),
    path(
        "services/<int:service_id>/unpublish",
        views.VendorServiceUnpublishView.as_view(),
        name="vendor-service-unpublish",
    ),
    path(
        "shops/<int:shop_id>/schedule",
        views.VendorShopScheduleView.as_view(),
        name="vendor-shop-schedule",
    ),
    path(
        "shops/<int:shop_id>/closures",
        views.VendorShopClosureListCreateView.as_view(),
        name="vendor-shop-closures",
    ),
    path(
        "shops/<int:shop_id>/closures/<int:closure_id>",
        views.VendorShopClosureDetailView.as_view(),
        name="vendor-shop-closure",
    ),
    path("bookings", views.VendorBookingListView.as_view(), name="vendor-bookings"),
    path(
        "bookings/<int:booking_id>",
        views.VendorBookingDetailView.as_view(),
        name="vendor-booking-detail",
    ),
    path(
        "bookings/<int:booking_id>/accept",
        views.VendorBookingAcceptView.as_view(),
        name="vendor-booking-accept",
    ),
    path(
        "bookings/<int:booking_id>/decline",
        views.VendorBookingDeclineView.as_view(),
        name="vendor-booking-decline",
    ),
]

customer_urlpatterns = [
    path("bookings", views.BookingListCreateView.as_view(), name="bookings"),
    path("bookings/<int:booking_id>", views.BookingDetailView.as_view(), name="booking-detail"),
    path(
        "bookings/<int:booking_id>/cancel",
        views.BookingCancelView.as_view(),
        name="booking-cancel",
    ),
]

admin_urlpatterns = [
    path("bookings", views.AdminBookingListView.as_view(), name="admin-bookings"),
    path(
        "bookings/<int:booking_id>",
        views.AdminBookingDetailView.as_view(),
        name="admin-booking-detail",
    ),
]
