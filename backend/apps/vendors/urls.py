from django.urls import path

from . import views

urlpatterns = [
    path("shops", views.VendorShopListCreateView.as_view(), name="vendor-shops"),
]
