from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from accounts.models import User
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationHistoryLog,
    VerificationStatus,
)
from bookings.models import (
    Complaint,
    ComplaintStatus,
    ReviewReport,
    ReportStatus,
)
from api.v1.verification.serializers import (
    VerificationDocumentSerializer,
    VerificationHistoryLogSerializer,
)


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "is_superuser",
        ]


class AdminVerificationListSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.user.full_name", read_only=True)
    professional_email = serializers.CharField(source="professional.user.email", read_only=True)
    professional_phone = serializers.CharField(source="professional.user.phone", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    documents_count = serializers.IntegerField(source="documents.count", read_only=True)

    class Meta:
        model = ProfessionalVerification
        fields = [
            "id",
            "professional",
            "professional_name",
            "professional_email",
            "professional_phone",
            "status",
            "status_display",
            "documents_count",
            "submitted_at",
            "reviewed_at",
            "rejection_reason",
            "created_at",
        ]


class AdminVerificationDetailSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.user.full_name", read_only=True)
    professional_email = serializers.CharField(source="professional.user.email", read_only=True)
    professional_phone = serializers.CharField(source="professional.user.phone", read_only=True)
    professional_title = serializers.CharField(source="professional.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.full_name", read_only=True, default=None)
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    history_logs = VerificationHistoryLogSerializer(many=True, read_only=True)

    class Meta:
        model = ProfessionalVerification
        fields = [
            "id",
            "professional",
            "professional_name",
            "professional_email",
            "professional_phone",
            "professional_title",
            "status",
            "status_display",
            "submitted_at",
            "reviewed_at",
            "reviewed_by_name",
            "rejection_reason",
            "expires_at",
            "documents",
            "history_logs",
            "created_at",
            "updated_at",
        ]


class AdminVerificationActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AdminComplaintListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    professional_name = serializers.CharField(source="professional.full_name", read_only=True, default=None)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "customer_name",
            "professional_name",
            "category",
            "category_display",
            "subject",
            "status",
            "status_display",
            "priority",
            "created_at",
        ]


class AdminComplaintDetailSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_email = serializers.CharField(source="customer.email", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    professional_name = serializers.CharField(source="professional.full_name", read_only=True, default=None)
    professional_email = serializers.CharField(source="professional.email", read_only=True, default=None)
    booking_number = serializers.CharField(source="booking.booking_number", read_only=True, default=None)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    resolved_by_name = serializers.CharField(source="resolved_by.full_name", read_only=True, default=None)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "customer",
            "customer_name",
            "customer_email",
            "customer_phone",
            "professional",
            "professional_name",
            "professional_email",
            "booking_number",
            "category",
            "category_display",
            "subject",
            "description",
            "status",
            "status_display",
            "priority",
            "resolution",
            "admin_notes",
            "resolved_by_name",
            "resolved_at",
            "created_at",
            "updated_at",
        ]


class AdminComplaintActionSerializer(serializers.Serializer):
    resolution = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")


class AdminReviewReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    review_rating = serializers.IntegerField(source="review.rating", read_only=True)
    review_comment = serializers.CharField(source="review.comment", read_only=True)
    review_customer = serializers.CharField(source="review.customer.full_name", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ReviewReport
        fields = [
            "id",
            "review",
            "review_rating",
            "review_comment",
            "review_customer",
            "reporter",
            "reporter_name",
            "reason",
            "reason_display",
            "description",
            "status",
            "status_display",
            "admin_notes",
            "created_at",
        ]


class AdminReviewReportActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["resolved", "dismissed"])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")


class AdminHealthcareOrganizationSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    type_display = serializers.CharField(source="get_organization_type_display", read_only=True)
    status_display = serializers.CharField(source="get_verification_status_display", read_only=True)
    staff_count = serializers.SerializerMethodField()

    class Meta:
        from healthcare.models import HealthcareOrganization
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
            "status_display",
            "rejection_reason",
            "owner_name",
            "owner_email",
            "staff_count",
            "created_at",
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_staff_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class AdminHealthcareProfessionalSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="professional.full_name", read_only=True)
    email = serializers.CharField(source="professional.email", read_only=True)
    phone = serializers.CharField(source="professional.phone", read_only=True)
    specialty_display = serializers.CharField(source="get_clinical_specialty_display", read_only=True)

    class Meta:
        from healthcare.models import HealthcareProfessionalProfile
        model = HealthcareProfessionalProfile
        fields = [
            "id",
            "professional",
            "name",
            "email",
            "phone",
            "medical_degree",
            "clinical_specialty",
            "specialty_display",
            "registration_number",
            "registration_council",
            "years_of_clinical_exp",
            "is_license_verified",
            "verified_at",
            "created_at",
        ]