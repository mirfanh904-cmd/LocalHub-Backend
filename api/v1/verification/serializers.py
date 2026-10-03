from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationHistoryLog,
    DocumentType,
)


class VerificationHistoryLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = VerificationHistoryLog
        fields = [
            "id",
            "previous_status",
            "new_status",
            "action",
            "performed_by_name",
            "reason",
            "notes",
            "created_at",
        ]

    @extend_schema_field(serializers.CharField())
    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.full_name or obj.performed_by.email
        return "System"


class VerificationDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalVerificationDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "document_number",
            "status",
            "rejection_reason",
            "download_url",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField())
    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/v1/verification/documents/{obj.id}/download/"
        if request:
            return request.build_absolute_uri(path)
        return path


class VerificationDocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    document_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    file = serializers.FileField(help_text="KYC document file (PDF, PNG, JPEG up to 5MB)")


class VerificationDetailSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.user.full_name", read_only=True)
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ProfessionalVerification
        fields = [
            "id",
            "professional_name",
            "status",
            "status_display",
            "submitted_at",
            "reviewed_at",
            "rejection_reason",
            "expires_at",
            "documents",
            "created_at",
            "updated_at",
        ]
