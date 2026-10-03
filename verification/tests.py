import io
import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import ProfessionalProfile
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationStatus,
    DocumentStatus,
    DocumentType,
)
from verification.services import VerificationService
from verification.validators import validate_verification_document
from verification.trust_score_service import TrustScoreService
from verification.expiry_service import DocumentExpiryService

User = get_user_model()


class VerificationDomainAndSecurityTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.worker_user = User.objects.create_user(
            email="pro_kcy@localhub.com",
            password="password123",
            first_name="Jane",
            last_name="Worker",
            role="PROFESSIONAL",
        )
        self.profile = ProfessionalProfile.objects.create(
            user=self.worker_user,
            professional_title="Certified Cleaner",
            experience_years=4,
            minimum_charge=Decimal("150.00"),
        )
        self.other_user = User.objects.create_user(
            email="other_cust@localhub.com",
            password="password123",
            first_name="John",
            last_name="Customer",
            role="CUSTOMER",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin_audit@localhub.com",
            password="password123",
            first_name="Admin",
            last_name="Super",
            role="ADMIN",
        )

        # Valid PDF header sample
        self.valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
        self.valid_pdf = SimpleUploadedFile(
            "aadhaar_card.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )

    def test_document_validation(self):
        # 1. Valid PDF should pass
        validate_verification_document(self.valid_pdf)

        # 2. Oversized file (>5MB) should fail
        large_content = self.valid_pdf_content + b"0" * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile("big.pdf", large_content, content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_verification_document(large_file)

        # 3. Invalid extension should fail
        invalid_ext_file = SimpleUploadedFile("script.exe", b"binary", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_verification_document(invalid_ext_file)

        # 4. Spoofed extension with invalid header should fail
        fake_pdf = SimpleUploadedFile("malicious.pdf", b"NOT_A_REAL_PDF", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_verification_document(fake_pdf)

    def test_verification_workflow_and_history_logging(self):
        verification = VerificationService.get_verification(self.profile)
        self.assertEqual(verification.status, VerificationStatus.DRAFT)

        # Cannot submit without document
        with self.assertRaises(ValidationError):
            VerificationService.submit_for_review(verification, performed_by=self.worker_user)

        # Upload document
        doc = VerificationService.upload_document(
            verification=verification,
            document_file=self.valid_pdf,
            document_type=DocumentType.AADHAAR,
            document_number="1234-5678-9012",
            performed_by=self.worker_user,
        )
        self.assertEqual(doc.status, DocumentStatus.PENDING)

        # Now submit should succeed
        verification = VerificationService.submit_for_review(verification, performed_by=self.worker_user)
        self.assertEqual(verification.status, VerificationStatus.PENDING)

        # Admin moves to under review
        verification = VerificationService.mark_under_review(verification, admin=self.admin_user, notes="Checking UIDAI validity")
        self.assertEqual(verification.status, VerificationStatus.UNDER_REVIEW)

        # Admin approves
        verification = VerificationService.approve_verification(verification, admin=self.admin_user, notes="Verified successfully")
        self.assertEqual(verification.status, VerificationStatus.APPROVED)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_verified)

        # Verify audit history logs exist and are ordered chronologically
        logs = list(VerificationService.get_history_logs(verification))
        self.assertTrue(len(logs) >= 4)
        actions = [log.action for log in logs]
        self.assertIn("approved", actions)
        self.assertIn("under_review", actions)
        self.assertIn("submitted", actions)
        self.assertIn("document_uploaded", actions)

    def test_secure_document_download_permissions(self):
        verification = VerificationService.get_verification(self.profile)
        doc = VerificationService.upload_document(
            verification=verification,
            document_file=self.valid_pdf,
            document_type=DocumentType.AADHAAR,
            performed_by=self.worker_user,
        )

        download_url = f"/api/v1/verification/documents/{doc.id}/download/"

        # 1. Anonymous access is denied
        self.client.force_authenticate(user=None)
        res = self.client.get(download_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Other customer access is forbidden (IDOR protection)
        self.client.force_authenticate(user=self.other_user)
        res = self.client.get(download_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Document owner access is permitted
        self.client.force_authenticate(user=self.worker_user)
        res = self.client.get(download_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 4. Admin access is permitted
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(download_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_trust_score_calculation(self):
        # Initial unverified profile score
        breakdown = TrustScoreService.calculate_score_for_profile(self.profile)
        self.assertEqual(breakdown["base_score"], 50)
        self.assertEqual(breakdown["verification_points"], 0)
        self.assertEqual(breakdown["total_score"], 50)
        self.assertEqual(breakdown["tier"], "Good")

        # After KYC approval (+25 points)
        verification = VerificationService.get_verification(self.profile)
        VerificationService.upload_document(verification, self.valid_pdf, DocumentType.AADHAAR)
        VerificationService.submit_for_review(verification, self.worker_user)
        VerificationService.approve_verification(verification, self.admin_user)

        self.profile.refresh_from_db()
        breakdown = TrustScoreService.calculate_score_for_profile(self.profile)
        self.assertEqual(breakdown["verification_points"], 25)
        self.assertEqual(breakdown["total_score"], 75)
        self.assertEqual(breakdown["tier"], "Trusted")

    def test_document_expiry_processing(self):
        verification = VerificationService.get_verification(self.profile)
        doc = VerificationService.upload_document(verification, self.valid_pdf, DocumentType.DRIVING_LICENSE)
        VerificationService.submit_for_review(verification, self.worker_user)
        VerificationService.approve_verification(verification, self.admin_user)

        # Set document expiry date in the past
        doc.ocr_expiry_date = datetime.date.today() - datetime.timedelta(days=1)
        doc.save(update_fields=["ocr_expiry_date"])

        # Run expiry service
        result = DocumentExpiryService.check_and_expire_documents(performed_by=self.admin_user)
        self.assertGreaterEqual(result["expired_documents_count"], 1)

        verification.refresh_from_db()
        self.assertEqual(verification.status, VerificationStatus.EXPIRED)
        self.assertFalse(self.profile.is_verified)
