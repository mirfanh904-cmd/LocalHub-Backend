import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel


class PayoutStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class PayoutMethod(models.TextChoices):
    BANK_TRANSFER = "BANK_TRANSFER", "Direct Bank Transfer (NEFT/IMPS)"
    UPI = "UPI", "UPI Instant Settlement"


class ProfessionalPayout(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    payout_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique payout identifier (e.g. PO-2026-1001).",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payout_requests",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    payout_method = models.CharField(
        max_length=20,
        choices=PayoutMethod.choices,
        default=PayoutMethod.UPI,
    )
    account_details = models.JSONField(
        default=dict,
        help_text="Masked bank details (acc_number, ifsc) or upi_id.",
    )
    status = models.CharField(
        max_length=20,
        choices=PayoutStatus.choices,
        default=PayoutStatus.REQUESTED,
        db_index=True,
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_payouts",
    )
    admin_notes = models.TextField(
        blank=True,
    )
    failure_reason = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "payments_professional_payout"
        ordering = ["-created_at"]
        verbose_name = "Professional Payout"
        verbose_name_plural = "Professional Payouts"

    def __str__(self):
        return f"{self.payout_reference} (₹{self.amount}) - {self.professional.email} [{self.status}]"
