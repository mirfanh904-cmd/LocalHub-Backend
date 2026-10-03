from rest_framework import serializers
from services.models import ServiceGroup


class ServiceGroupCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGroup
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon_class",
            "theme_color",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
