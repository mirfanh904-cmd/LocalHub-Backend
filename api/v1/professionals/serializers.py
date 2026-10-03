from rest_framework import serializers
from accounts.models import (
    ProfessionalProfile,
    ProfessionalService,
    Skill,
    Language,
)


class ProfessionalServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_slug = serializers.CharField(source="service.slug", read_only=True)

    class Meta:
        model = ProfessionalService
        fields = [
            "id",
            "service_name",
            "service_slug",
            "custom_price",
            "estimated_duration",
            "is_active",
        ]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "name", "code"]


class ProfessionalListSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    avatar = serializers.ImageField(source="profile_photo", read_only=True)
    title = serializers.CharField(source="professional_title", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id",
            "user_id",
            "full_name",
            "title",
            "bio",
            "avatar",
            "experience_years",
            "average_rating",
            "reviews_count",
            "is_verified",
            "minimum_charge",
            "hourly_rate",
            "availability_status",
        ]


class ProfessionalDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    avatar = serializers.ImageField(source="profile_photo", read_only=True)
    title = serializers.CharField(source="professional_title", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    services = ProfessionalServiceSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "avatar",
            "title",
            "bio",
            "experience_years",
            "average_rating",
            "reviews_count",
            "is_verified",
            "minimum_charge",
            "hourly_rate",
            "working_radius",
            "availability_status",
            "services",
            "skills",
            "languages",
        ]


class TrustScoreSignalSerializer(serializers.Serializer):
    name = serializers.CharField()
    status = serializers.CharField()
    points = serializers.IntegerField()
    description = serializers.CharField()


class TrustScoreResponseSerializer(serializers.Serializer):
    base_score = serializers.IntegerField()
    verification_points = serializers.IntegerField()
    ratings_points = serializers.IntegerField()
    bookings_points = serializers.IntegerField()
    complaint_deductions = serializers.IntegerField()
    total_score = serializers.IntegerField()
    tier = serializers.CharField()
    signals = TrustScoreSignalSerializer(many=True)
