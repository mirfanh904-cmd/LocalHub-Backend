from rest_framework import serializers

from services.models import Category


class CategorySerializer(serializers.ModelSerializer):

    service_group = serializers.StringRelatedField()

    class Meta:

        model = Category

        fields = (
            "id",
            "service_group",
            "name",
            "slug",
            "short_description",
            "description",
            "cover_image",
            "bootstrap_icon",
            "theme_color",
            "display_order",
            "is_featured",
        )