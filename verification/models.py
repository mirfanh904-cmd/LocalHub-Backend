from django.conf import settings
from django.db import models
from accounts.models import ProfessionalProfile


class VerificationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"
    SUSPENDED = "suspended", "Suspended"


class ProfessionalVerification(models.Model):
    professional = models.OneToOneField(ProfessionalProfile, on_delete=models.CASCADE, related_name="verification")
    status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_verifications")
    rejection_reason = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Professional Verification"
        verbose_name_plural = "Professional Verifications"

    def __str__(self):
        return f"{self.professional} - {self.get_status_display()}"


class DocumentType(models.TextChoices):
    AADHAAR = "aadhaar", "Aadhaar Card"
    PASSPORT = "passport", "Passport"
    VOTER_ID = "voter_id", "Voter ID"
    DRIVING_LICENSE = "driving_license", "Driving Licence"
    ADDRESS_PROOF = "address_proof", "Address Proof"
    SELFIE = "selfie", "Selfie"
    EXPERIENCE_CERTIFICATE = "experience_certificate", "Experience Certificate"
    TRADE_LICENSE = "trade_license", "Trade License"
    MEDICAL_COUNCIL_REGISTRATION = "medical_council_registration", "State Medical Council Registration Certificate"
    NURSING_COUNCIL_LICENSE = "nursing_council_license", "Nursing Council License"
    CLINICAL_DEGREE = "clinical_degree", "Medical / Nursing / Physio Degree Certificate"


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"

    
class ProfessionalVerificationDocument(models.Model):
    verification = models.ForeignKey(ProfessionalVerification, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=40, choices=DocumentType.choices)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    document_file = models.FileField(upload_to="verification/documents/")
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.PENDING, db_index=True)

    ocr_name = models.CharField(max_length=255, blank=True)
    ocr_document_number = models.CharField(max_length=100, blank=True)
    ocr_date_of_birth = models.DateField(null=True, blank=True)
    ocr_expiry_date = models.DateField(null=True, blank=True)
    ocr_raw_text = models.TextField(blank=True)
    ocr_processed_at = models.DateTimeField(null=True, blank=True)
    ocr_success = models.BooleanField(default=False)
    ocr_error = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_documents")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Verification Document"
        verbose_name_plural = "Verification Documents"
        constraints = [
            models.UniqueConstraint(
                fields=["verification", "document_type", "document_number"],
                name="unique_verification_document"
            )
        ]
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.verification.professional}"


class VerificationHistoryLog(models.Model):
    verification = models.ForeignKey(
        ProfessionalVerification,
        on_delete=models.CASCADE,
        related_name="history_logs",
    )
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    action = models.CharField(max_length=100)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verification_audit_actions",
    )
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Verification History Log"
        verbose_name_plural = "Verification History Logs"

    def __str__(self):
        return f"{self.verification.professional} - {self.action} ({self.new_status}) at {self.created_at}"