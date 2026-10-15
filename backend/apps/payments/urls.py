from django.urls import path

from . import views

urlpatterns = [
    path("methods", views.PaymentMethodListView.as_view(), name="payment-methods"),
    path(
        "azampay/callback/<str:token>",
        views.AzamPayCallbackView.as_view(),
        name="azampay-callback",
    ),
]

simulator_urlpatterns = [
    path("pushes", views.SimulatorPushListView.as_view(), name="azampay-sim-pushes"),
    path(
        "pushes/<str:reference>/approve",
        views.SimulatorPushDecisionView.as_view(approve=True),
        name="azampay-sim-approve",
    ),
    path(
        "pushes/<str:reference>/reject",
        views.SimulatorPushDecisionView.as_view(approve=False),
        name="azampay-sim-reject",
    ),
]
