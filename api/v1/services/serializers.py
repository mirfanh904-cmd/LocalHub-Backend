from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from services.models import (
    ServiceGroup,
    Category,
    Service,
    ServicePackage,
    ServicePackageInclude,
    ServiceRequirement,
    ServiceFAQ,
)



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "bootstrap_icon",
            "theme_color",
            "display_order",
        ]


class ServiceGroupSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = ServiceGroup
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "icon_class",
            "cover_image",
            "theme_color",
            "display_order",
            "is_featured",
            "categories",
        ]


class ServicePackageFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePackageInclude
        fields = ["id", "title", "icon", "sort_order"]


class ServicePackageSerializer(serializers.ModelSerializer):
    features = ServicePackageFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = ServicePackage
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "price",
            "duration",
            "is_popular",
            "sort_order",
            "features",
        ]


class ServiceRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequirement
        fields = [
            "id",
            "label",
            "field_name",
            "field_type",
            "placeholder",
            "help_text",
            "choices",
            "default_value",
            "required",
            "sort_order",
        ]


class ServiceFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFAQ
        fields = ["id", "question", "answer", "sort_order"]


class ServiceListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    service_group_name = serializers.CharField(source="category.service_group.name", read_only=True)
    service_group_slug = serializers.CharField(source="category.service_group.slug", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "slug",
            "category_name",
            "category_slug",
            "service_group_name",
            "service_group_slug",
            "short_description",
            "cover_image",
            "icon_class",
            "starting_price",
            "estimated_duration",
            "theme_color",
            "average_rating",
            "reviews_count",
            "is_featured",
        ]


class ServiceDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    service_group_name = serializers.CharField(source="category.service_group.name", read_only=True)
    service_group_slug = serializers.CharField(source="category.service_group.slug", read_only=True)
    packages = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    faqs = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "slug",
            "category_name",
            "category_slug",
            "service_group_name",
            "service_group_slug",
            "short_description",
            "description",
            "cover_image",
            "icon_class",
            "starting_price",
            "estimated_duration",
            "theme_color",
            "average_rating",
            "reviews_count",
            "is_featured",
            "packages",
            "requirements",
            "faqs",
        ]

    @extend_schema_field(ServicePackageSerializer(many=True))
    def get_packages(self, obj):
        packages = obj.packages.filter(is_active=True).prefetch_related("features")
        return ServicePackageSerializer(packages, many=True).data

    @extend_schema_field(ServiceRequirementSerializer(many=True))
    def get_requirements(self, obj):
        requirements = obj.requirements.filter(is_active=True).order_by("sort_order", "id")
        return ServiceRequirementSerializer(requirements, many=True).data

    @extend_schema_field(ServiceFAQSerializer(many=True))
    def get_faqs(self, obj):
        faqs = obj.faqs.all().order_by("sort_order", "id")
        return ServiceFAQSerializer(faqs, many=True).data


# Alias for backward compatibility
ServiceSerializer = ServiceListSerializer