from django.urls import path

from . import views

admin_urlpatterns = [
    path("audit-events", views.AdminAuditEventListView.as_view(), name="admin-audit-event-list"),
]
