from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "created_at",
            "actor",
            "actor_email",
            "actor_role",
            "action",
            "action_label",
            "target_type",
            "target_id",
            "target_repr",
            "metadata",
            "ip_address",
            "user_agent",
        ]
        read_only_fields = fields


class AuditFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
