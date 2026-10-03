from rest_framework import serializers
from services.models import Category


class CategoryCRUDSerializer(serializers.ModelSerializer):
    service_group_name = serializers.ReadOnlyField(source="service_group.name")

    class Meta:
        model = Category
        fields = [
            "id",
            "service_group",
            "service_group_name",
            "name",
            "slug",
            "description",
            "bootstrap_icon",
            "display_order",
            "is_featured",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
