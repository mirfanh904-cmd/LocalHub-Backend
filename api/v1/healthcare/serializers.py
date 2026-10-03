from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from healthcare.models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareOrganization,
    OrganizationMembership,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
    AppointmentType,
    ClinicalSpecialty,
    OrganizationType,
    OrganizationRole,
)
from services.models import Service, ServicePackage
from accounts.models import User, ProfessionalProfile
from api.v1.bookings.serializers import BookingDetailSerializer


class HealthcareServicePackageSerializer(serializers.ModelSerializer):
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
        ]


class HealthcareServiceSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source="category.id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    service_group_name = serializers.CharField(source="category.service_group.name", read_only=True)
    service_group_slug = serializers.CharField(source="category.service_group.slug", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    packages = HealthcareServicePackageSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "starting_price",
            "estimated_duration",
            "category_id",
            "category_name",
            "category_slug",
            "service_group_name",
            "service_group_slug",
            "cover_image_url",
            "packages",
            "is_featured",
            "is_active",
            "average_rating",
            "reviews_count",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        slug = obj.slug or ""
        fallbacks = {
            "doctor-home-consultation": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?q=80&w=800&auto=format&fit=crop",
            "post-operative-home-nursing": "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?q=80&w=800&auto=format&fit=crop",
            "orthopedic-physiotherapy-session": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=800&auto=format&fit=crop",
            "elderly-caregiving-daily": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?q=80&w=800&auto=format&fit=crop",
            "full-body-health-checkup-lab": "https://images.unsplash.com/photo-1579154204601-01588f351e67?q=80&w=800&auto=format&fit=crop",
        }
        for k, v in fallbacks.items():
            if k in slug:
                return v
        return "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?q=80&w=800&auto=format&fit=crop"


class PatientMedicalProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = PatientMedicalProfile
        fields = [
            "id",
            "user_name",
            "user_email",
            "date_of_birth",
            "gender",
            "blood_group",
            "chronic_conditions",
            "allergies",
            "mobility_assistance",
            "special_accommodations",
            "updated_at",
        ]


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id",
            "name",
            "relationship",
            "phone_number",
            "is_primary",
            "created_at",
        ]


class HealthcareProfessionalProfileSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.full_name", read_only=True)
    professional_email = serializers.CharField(source="professional.email", read_only=True)
    specialty_display = serializers.CharField(source="get_clinical_specialty_display", read_only=True)

    class Meta:
        model = HealthcareProfessionalProfile
        fields = [
            "id",
            "professional",
            "professional_name",
            "professional_email",
            "registration_number",
            "registration_council",
            "medical_degree",
            "clinical_specialty",
            "specialty_display",
            "years_of_clinical_exp",
            "is_license_verified",
            "verified_at",
            "created_at",
        ]


class HealthcareProfessionalPublicSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="professional.id", read_only=True)
    name = serializers.CharField(source="professional.full_name", read_only=True)
    specialty = serializers.CharField(source="get_clinical_specialty_display", read_only=True)
    specialty_code = serializers.CharField(source="clinical_specialty", read_only=True)
    degree = serializers.CharField(source="medical_degree", read_only=True)
    registration_number = serializers.CharField(read_only=True)
    registration_council = serializers.CharField(read_only=True)
    experience_years = serializers.IntegerField(source="years_of_clinical_exp", read_only=True)
    is_verified = serializers.BooleanField(source="is_license_verified", read_only=True)
    hourly_rate = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()

    class Meta:
        model = HealthcareProfessionalProfile
        fields = [
            "id",
            "name",
            "specialty",
            "specialty_code",
            "degree",
            "registration_number",
            "registration_council",
            "experience_years",
            "is_verified",
            "hourly_rate",
            "average_rating",
            "reviews_count",
            "profile_photo",
            "bio",
        ]

    @extend_schema_field(serializers.CharField())
    def get_hourly_rate(self, obj):
        pro_profile = getattr(obj.professional, "professional_profile", None)
        if pro_profile and pro_profile.hourly_rate:
            return str(pro_profile.hourly_rate)
        return "799.00"

    @extend_schema_field(serializers.CharField())
    def get_average_rating(self, obj):
        pro_profile = getattr(obj.professional, "professional_profile", None)
        return str(pro_profile.average_rating if pro_profile else "4.9")

    @extend_schema_field(serializers.IntegerField())
    def get_reviews_count(self, obj):
        pro_profile = getattr(obj.professional, "professional_profile", None)
        return pro_profile.reviews_count if pro_profile else 50

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_photo(self, obj):
        pro_profile = getattr(obj.professional, "professional_profile", None)
        if pro_profile and pro_profile.profile_photo:
            return pro_profile.profile_photo.url
        user_prof = getattr(obj.professional, "profile", None)
        if user_prof and user_prof.profile_picture:
            return user_prof.profile_picture.url
        spec = str(obj.clinical_specialty).lower()
        if "nurs" in spec:
            return "https://images.unsplash.com/photo-1594824813501-44755174092b?q=80&w=400&auto=format&fit=crop"
        elif "physio" in spec:
            return "https://images.unsplash.com/photo-1622253692010-333f2da6031d?q=80&w=400&auto=format&fit=crop"
        return "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?q=80&w=400&auto=format&fit=crop"

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_bio(self, obj):
        pro_profile = getattr(obj.professional, "professional_profile", None)
        return pro_profile.bio if pro_profile else ""


class HealthcareOrganizationSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    type_display = serializers.CharField(source="get_organization_type_display", read_only=True)
    services_count = serializers.IntegerField(source="services.count", read_only=True)
    staff_count = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = HealthcareOrganization
        fields = [
            "id",
            "name",
            "slug",
            "organization_type",
            "type_display",
            "registration_number",
            "license_number",
            "contact_email",
            "contact_phone",
            "address",
            "city",
            "state",
            "postal_code",
            "description",
            "is_verified",
            "verification_status",
            "owner_name",
            "services_count",
            "staff_count",
            "average_rating",
            "reviews_count",
            "logo_url",
            "created_at",
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_staff_count(self, obj):
        return obj.memberships.filter(is_active=True).count()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_logo_url(self, obj):
        if obj.logo:
            return obj.logo.url
        fallbacks = {
            "hospital": "https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?q=80&w=400&auto=format&fit=crop",
            "clinic": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=400&auto=format&fit=crop",
            "diagnostic_center": "https://images.unsplash.com/photo-1579154204601-01588f351e67?q=80&w=400&auto=format&fit=crop",
            "agency": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?q=80&w=400&auto=format&fit=crop",
        }
        return fallbacks.get(obj.organization_type, "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=400&auto=format&fit=crop")


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    role = serializers.CharField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    specialty = serializers.SerializerMethodField()
    degree = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "organization",
            "user",
            "user_name",
            "user_email",
            "role",
            "role_display",
            "specialty",
            "degree",
            "is_active",
            "joined_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_specialty(self, obj):
        h_profile = getattr(obj.user, "healthcare_profile", None)
        return h_profile.get_clinical_specialty_display() if h_profile else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_degree(self, obj):
        h_profile = getattr(obj.user, "healthcare_profile", None)
        return h_profile.medical_degree if h_profile else None


class PatientInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInstruction
        fields = [
            "id",
            "title",
            "instruction_text",
            "requires_fasting",
            "fasting_hours",
            "is_acknowledged",
            "acknowledged_at",
            "created_at",
        ]


class MedicalVisitNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = MedicalVisitNote
        fields = [
            "id",
            "author",
            "author_name",
            "systolic_bp",
            "diastolic_bp",
            "heart_rate_bpm",
            "temperature_f",
            "oxygen_saturation",
            "clinical_observations",
            "care_recommendations",
            "created_at",
        ]
        read_only_fields = ["id", "author", "created_at"]


class MedicalVisitNoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalVisitNote
        fields = [
            "systolic_bp",
            "diastolic_bp",
            "heart_rate_bpm",
            "temperature_f",
            "oxygen_saturation",
            "clinical_observations",
            "care_recommendations",
        ]


class HealthcareAppointmentDetailSerializer(serializers.ModelSerializer):
    booking_details = BookingDetailSerializer(source="booking", read_only=True)
    patient_profile = PatientMedicalProfileSerializer(read_only=True)
    emergency_contact = EmergencyContactSerializer(read_only=True)
    instructions = PatientInstructionSerializer(many=True, read_only=True)
    medical_notes = MedicalVisitNoteSerializer(many=True, read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    appointment_type_display = serializers.CharField(source="get_appointment_type_display", read_only=True)

    class Meta:
        model = HealthcareAppointment
        fields = [
            "id",
            "booking_details",
            "organization",
            "organization_name",
            "patient_profile",
            "emergency_contact",
            "appointment_type",
            "appointment_type_display",
            "symptoms",
            "accessibility_needs",
            "pre_visit_instructions",
            "is_emergency",
            "instructions",
            "medical_notes",
            "created_at",
        ]


class HealthcareBookingCreateSerializer(serializers.Serializer):
    # Standard booking fields
    service = serializers.IntegerField(required=True, help_text="Service ID")
    package = serializers.IntegerField(required=False, allow_null=True, help_text="Package ID")
    address = serializers.IntegerField(required=True, help_text="Address ID")
    booking_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    end_time = serializers.TimeField(required=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    platform_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    tax = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    customer_note = serializers.CharField(required=False, allow_blank=True, default="")
    worker = serializers.UUIDField(required=False, allow_null=True, help_text="Optional requested worker UUID")
    organization_id = serializers.IntegerField(required=False, allow_null=True, help_text="Optional organization ID")

    # Healthcare specific fields
    appointment_type = serializers.ChoiceField(choices=AppointmentType.choices, required=True)
    symptoms = serializers.CharField(required=False, allow_blank=True, default="")
    accessibility_needs = serializers.CharField(required=False, allow_blank=True, default="")
    pre_visit_instructions = serializers.CharField(required=False, allow_blank=True, default="")
    emergency_contact_id = serializers.IntegerField(required=False, allow_null=True)
    is_emergency = serializers.BooleanField(required=False, default=False)
