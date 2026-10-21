from rest_framework.generics import ListAPIView

from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer, AuditFilterSerializer
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import AdminArea


class AdminAuditEventListView(ListAPIView):
    """The audit trail, newest first. Filters: `action` (exact, or a prefix ending in `.` such as
    `shop.`), `actor` (email contains), `actor_role`, `target_type`, `target_id`, `from`, `to`
    (dates)."""

    permission_classes = [AdminArea("audit")]
    serializer_class = AuditEventSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        params = self.request.query_params
        dates = AuditFilterSerializer(
            data={
                key: value
                for key, value in (("date_from", params.get("from")), ("date_to", params.get("to")))
                if value
            }
        )
        dates.is_valid(raise_exception=True)

        queryset = AuditEvent.objects.select_related("actor")
        action = params.get("action", "").strip()
        if action.endswith("."):
            queryset = queryset.filter(action__startswith=action)
        elif action:
            queryset = queryset.filter(action=action)
        if actor := params.get("actor", "").strip():
            queryset = queryset.filter(actor_email__icontains=actor)
        if actor_role := params.get("actor_role", "").strip():
            queryset = queryset.filter(actor_role=actor_role)
        if target_type := params.get("target_type", "").strip():
            queryset = queryset.filter(target_type=target_type)
        if target_id := params.get("target_id", "").strip():
            queryset = queryset.filter(target_id=target_id)
        if date_from := dates.validated_data.get("date_from"):
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to := dates.validated_data.get("date_to"):
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset
