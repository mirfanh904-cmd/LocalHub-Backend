from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from accounts.models import Address, User, UserProfile, ProfessionalProfile, Skill, Language
from healthcare.models import (
    HealthcareProfessionalProfile,
    HealthcareOrganization,
    OrganizationMembership,
    ClinicalSpecialty,
    OrganizationType,
    OrganizationRole,
)
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    DocumentType,
    VerificationStatus,
)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "full_name",
            "phone",
            "address_type",
            "house_name",
            "area",
            "landmark",
            "city",
            "state",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    is_verified = serializers.SerializerMethodField()
    professional_profile_id = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    is_healthcare_pro = serializers.SerializerMethodField()
    is_org_owner = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "role",
            "profile_picture",
            "bio",
            "city",
            "is_verified",
            "is_healthcare_pro",
            "is_org_owner",
            "professional_profile_id",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "created_at"]

    @extend_schema_field(serializers.BooleanField())
    def get_is_verified(self, obj):
        profile = getattr(obj, "professional_profile", None)
        if profile:
            return profile.is_verified
        return False

    @extend_schema_field(serializers.BooleanField())
    def get_is_healthcare_pro(self, obj):
        return hasattr(obj, "healthcare_profile")

    @extend_schema_field(serializers.BooleanField())
    def get_is_org_owner(self, obj):
        return obj.owned_organizations.exists()

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_professional_profile_id(self, obj):
        profile = getattr(obj, "professional_profile", None)
        return profile.id if profile else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_picture(self, obj):
        user_profile = getattr(obj, "profile", None)
        if user_profile and user_profile.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(user_profile.profile_picture.url)
            return user_profile.profile_picture.url
        prof_profile = getattr(obj, "professional_profile", None)
        if prof_profile and prof_profile.profile_photo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(prof_profile.profile_photo.url)
            return prof_profile.profile_photo.url
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_bio(self, obj):
        user_profile = getattr(obj, "profile", None)
        if user_profile and user_profile.bio:
            return user_profile.bio
        prof_profile = getattr(obj, "professional_profile", None)
        if prof_profile and prof_profile.bio:
            return prof_profile.bio
        return ""

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_city(self, obj):
        user_profile = getattr(obj, "profile", None)
        if user_profile and user_profile.city:
            return user_profile.city
        prof_profile = getattr(obj, "professional_profile", None)
        if prof_profile and hasattr(prof_profile, "city"):
            return getattr(prof_profile, "city", "")
        return ""


class UserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def update(self, instance, validated_data):
        if "first_name" in validated_data:
            instance.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            instance.last_name = validated_data["last_name"]
        if "phone" in validated_data:
            instance.phone = validated_data["phone"]
        instance.save()

        user_profile, _ = UserProfile.objects.get_or_create(user=instance)
        if "bio" in validated_data:
            user_profile.bio = validated_data["bio"]
        if "city" in validated_data:
            user_profile.city = validated_data["city"]
        user_profile.save()

        prof_profile = getattr(instance, "professional_profile", None)
        if prof_profile:
            if "bio" in validated_data:
                prof_profile.bio = validated_data["bio"]
            if "city" in validated_data and hasattr(prof_profile, "city"):
                setattr(prof_profile, "city", validated_data["city"])
            prof_profile.save()

        return instance


class UserCapabilitiesSerializer(serializers.Serializer):
    is_customer = serializers.BooleanField(default=True)
    is_individual_pro = serializers.BooleanField()
    is_healthcare_pro = serializers.BooleanField()
    is_organization_owner = serializers.BooleanField()
    is_organization_member = serializers.BooleanField()
    pro_verification_status = serializers.CharField(allow_null=True)
    organizations = serializers.ListField()


class BecomeIndividualProSerializer(serializers.Serializer):
    professional_title = serializers.CharField(max_length=150, required=True)
    bio = serializers.CharField(required=True)
    experience_years = serializers.IntegerField(min_value=0, required=True)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=299)
    working_radius = serializers.IntegerField(min_value=1, required=False, default=15)
    skills = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    document_type = serializers.CharField(required=False, default="aadhaar")
    document_number = serializers.CharField(required=False, allow_blank=True, default="")
    document_file = serializers.FileField(required=False, allow_null=True)


class BecomeHealthcareProSerializer(serializers.Serializer):
    medical_degree = serializers.CharField(max_length=150, required=True)
    clinical_specialty = serializers.ChoiceField(choices=ClinicalSpecialty.choices, required=True)
    registration_number = serializers.CharField(max_length=100, required=True)
    registration_council = serializers.CharField(max_length=200, required=True)
    years_of_clinical_exp = serializers.IntegerField(min_value=0, required=True)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=799)
    bio = serializers.CharField(required=True)
    document_type = serializers.CharField(required=False, default="medical_council_registration")
    document_number = serializers.CharField(required=False, allow_blank=True, default="")
    document_file = serializers.FileField(required=False, allow_null=True)


class BecomeOrganizationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    organization_type = serializers.ChoiceField(choices=OrganizationType.choices, required=True)
    registration_number = serializers.CharField(max_length=100, required=True)
    license_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    contact_email = serializers.EmailField(required=True)
    contact_phone = serializers.CharField(max_length=20, required=True)
    address = serializers.CharField(required=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    state = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    postal_code = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    document_type = serializers.CharField(required=False, default="trade_license")
    document_file = serializers.FileField(required=False, allow_null=True)