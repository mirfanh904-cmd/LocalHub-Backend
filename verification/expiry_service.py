from django.utils import timezone
from django.db import transaction
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationStatus,
    DocumentStatus,
    VerificationHistoryLog,
)


class DocumentExpiryService:
    """
    Domain service to process expiring KYC documents and update verification status accordingly.
    """

    @classmethod
    @transaction.atomic
    def check_and_expire_documents(cls, performed_by=None):
        """
        Scans all active documents and verifications.
        Marks expired documents and updates associated verification status to EXPIRED.
        Returns a summary report dict.
        """
        today = timezone.now().date()
        now = timezone.now()

        expired_docs_count = 0
        expired_verifications_count = 0

        # 1. Process documents with ocr_expiry_date in the past
        expired_docs = ProfessionalVerificationDocument.objects.filter(
            ocr_expiry_date__lt=today,
            status=DocumentStatus.VERIFIED,
        )

        for doc in expired_docs:
            doc.status = DocumentStatus.REJECTED
            doc.rejection_reason = "Document has expired."
            doc.save(update_fields=["status", "rejection_reason"])
            expired_docs_count += 1

            verification = doc.verification
            if verification.status == VerificationStatus.APPROVED:
                prev_status = verification.status
                verification.status = VerificationStatus.EXPIRED
                verification.save(update_fields=["status"])
                expired_verifications_count += 1

                VerificationHistoryLog.objects.create(
                    verification=verification,
                    previous_status=prev_status,
                    new_status=VerificationStatus.EXPIRED,
                    action="expired",
                    performed_by=performed_by,
                    reason=f"Document {doc.get_document_type_display()} expired on {doc.ocr_expiry_date}.",
                    notes="Automatic expiration processing."
                )

        # 2. Process verifications with expires_at in the past
        expired_verifications = ProfessionalVerification.objects.filter(
            expires_at__lt=now,
            status=VerificationStatus.APPROVED,
        )

        for verification in expired_verifications:
            prev_status = verification.status
            verification.status = VerificationStatus.EXPIRED
            verification.save(update_fields=["status"])
            expired_verifications_count += 1

            VerificationHistoryLog.objects.create(
                verification=verification,
                previous_status=prev_status,
                new_status=VerificationStatus.EXPIRED,
                action="expired",
                performed_by=performed_by,
                reason="Verification term expired.",
                notes="Automatic expiration processing."
            )

        return {
            "expired_documents_count": expired_docs_count,
            "expired_verifications_count": expired_verifications_count,
            "processed_at": now.isoformat(),
        }
