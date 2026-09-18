from django.urls import path

from . import views

checkout_urlpatterns = [
    path("checkout", views.CheckoutView.as_view(), name="checkout"),
]
