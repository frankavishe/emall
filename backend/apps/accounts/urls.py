from django.urls import path

from . import views

urlpatterns = [
    path("register/customer", views.RegisterCustomerView.as_view(), name="register-customer"),
    path("register/vendor", views.RegisterVendorView.as_view(), name="register-vendor"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("refresh", views.RefreshView.as_view(), name="refresh"),
    path("me", views.MeView.as_view(), name="me"),
    path(
        "verify-email/request",
        views.VerifyEmailRequestView.as_view(),
        name="verify-email-request",
    ),
    path(
        "verify-email/confirm",
        views.VerifyEmailConfirmView.as_view(),
        name="verify-email-confirm",
    ),
]
