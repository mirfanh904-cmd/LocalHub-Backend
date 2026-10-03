from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationStatus,
    DocumentStatus,
    VerificationHistoryLog,
)
from .validators import validate_verification_document


class VerificationService:

    @staticmethod
    def get_or_create_verification(professional):
        verification, created = ProfessionalVerification.objects.get_or_create(
            professional=professional,
            defaults={"status": VerificationStatus.DRAFT},
        )
        return verification

    @staticmethod
    def create_verification(professional):
        return VerificationService.get_or_create_verification(professional)

    @staticmethod
    def get_verification(professional):
        return VerificationService.get_or_create_verification(professional)


    @staticmethod
    @transaction.atomic
    def submit_for_review(verification, performed_by=None):
        """
        Submit a verification request for admin review.
        Only Draft, Expired, and Rejected verifications can be submitted.
        Must have at least one document uploaded.
        """
        if verification.status not in [
            VerificationStatus.DRAFT,
            VerificationStatus.REJECTED,
            VerificationStatus.EXPIRED,
        ]:
            raise ValidationError(
                "Only Draft, Rejected, or Expired verification requests can be submitted."
            )

        if not verification.documents.exists():
            raise ValidationError(
                "Please upload at least one verification document before submitting."
            )

        previous_status = verification.status
        verification.status = VerificationStatus.PENDING
        verification.submitted_at = timezone.now()
        verification.reviewed_by = None
        verification.reviewed_at = None
        verification.rejection_reason = ""
        verification.save(
            update_fields=[
                "status",
                "submitted_at",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ]
        )

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=previous_status,
            new_status=VerificationStatus.PENDING,
            action="submitted",
            performed_by=performed_by or getattr(verification.professional, "user", None),
            notes="Professional submitted verification for administrative review.",
        )

        return verification

    @staticmethod
    @transaction.atomic
    def mark_under_review(verification, admin, notes=""):
        if verification.status != VerificationStatus.PENDING:
            raise ValidationError(
                "Only pending verification requests can be moved to under review."
            )

        previous_status = verification.status
        verification.status = VerificationStatus.UNDER_REVIEW
        verification.reviewed_by = admin
        verification.reviewed_at = timezone.now()
        verification.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=previous_status,
            new_status=VerificationStatus.UNDER_REVIEW,
            action="under_review",
            performed_by=admin,
            notes=notes or "Admin began reviewing verification dossier.",
        )

        return verification

    @staticmethod
    @transaction.atomic
    def approve_verification(verification, admin, notes=""):
        if verification.status not in [
            VerificationStatus.PENDING,
            VerificationStatus.UNDER_REVIEW,
        ]:
            raise ValidationError(
                "Only pending or under review verification requests can be approved."
            )

        previous_status = verification.status
        now = timezone.now()

        verification.status = VerificationStatus.APPROVED
        verification.reviewed_by = admin
        verification.reviewed_at = now
        verification.rejection_reason = ""
        verification.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ]
        )

        verification.documents.update(
            status=DocumentStatus.VERIFIED,
            reviewed_by=admin,
            reviewed_at=now,
            rejection_reason="",
        )

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=previous_status,
            new_status=VerificationStatus.APPROVED,
            action="approved",
            performed_by=admin,
            notes=notes or "Admin approved professional KYC verification.",
        )

        user = verification.professional.user
        if user.role != "ADMIN" and not user.is_staff and not user.is_superuser:
            user.role = "PROFESSIONAL"
            user.save(update_fields=["role", "updated_at"])

        return verification

    @staticmethod
    @transaction.atomic
    def reject_verification(verification, admin, reason, notes=""):
        if not reason:
            raise ValidationError("A rejection reason is required.")

        if verification.status not in [
            VerificationStatus.PENDING,
            VerificationStatus.UNDER_REVIEW,
        ]:
            raise ValidationError(
                "Only pending or under review verification requests can be rejected."
            )

        previous_status = verification.status
        now = timezone.now()

        verification.status = VerificationStatus.REJECTED
        verification.reviewed_by = admin
        verification.reviewed_at = now
        verification.rejection_reason = reason
        verification.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ]
        )

        verification.documents.update(
            status=DocumentStatus.REJECTED,
            reviewed_by=admin,
            reviewed_at=now,
            rejection_reason=reason,
        )

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=previous_status,
            new_status=VerificationStatus.REJECTED,
            action="rejected",
            performed_by=admin,
            reason=reason,
            notes=notes or "Admin rejected verification application.",
        )

        return verification

    @staticmethod
    @transaction.atomic
    def suspend_verification(verification, admin, reason="", notes=""):
        if verification.status != VerificationStatus.APPROVED:
            raise ValidationError(
                "Only approved verification requests can be suspended."
            )

        previous_status = verification.status
        now = timezone.now()

        verification.status = VerificationStatus.SUSPENDED
        verification.reviewed_by = admin
        verification.reviewed_at = now
        verification.rejection_reason = reason
        verification.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ]
        )

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=previous_status,
            new_status=VerificationStatus.SUSPENDED,
            action="suspended",
            performed_by=admin,
            reason=reason,
            notes=notes or "Admin suspended professional verification.",
        )

        return verification

    @staticmethod
    @transaction.atomic
    def upload_document(verification, document_file, document_type, document_number="", performed_by=None):
        """
        Validates and uploads a KYC verification document.
        """
        validate_verification_document(document_file)

        doc = ProfessionalVerificationDocument.objects.create(
            verification=verification,
            document_type=document_type,
            document_number=document_number,
            document_file=document_file,
            status=DocumentStatus.PENDING,
        )

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=verification.status,
            new_status=verification.status,
            action="document_uploaded",
            performed_by=performed_by or getattr(verification.professional, "user", None),
            notes=f"Uploaded {doc.get_document_type_display()} (ID: {doc.id}).",
        )

        return doc

    @staticmethod
    @transaction.atomic
    def delete_document(document, performed_by=None):
        verification = document.verification
        doc_type_name = document.get_document_type_display()
        doc_id = document.id

        document.delete()

        VerificationHistoryLog.objects.create(
            verification=verification,
            previous_status=verification.status,
            new_status=verification.status,
            action="document_deleted",
            performed_by=performed_by,
            notes=f"Deleted {doc_type_name} (ID: {doc_id}).",
        )

    @staticmethod
    def get_documents(verification):
        return verification.documents.all()

    @staticmethod
    def get_history_logs(verification):
        return verification.history_logs.select_related("performed_by").order_by("-created_at")