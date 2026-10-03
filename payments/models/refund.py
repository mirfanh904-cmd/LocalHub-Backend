import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel
from .payment import Payment


class RefundStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Admin Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    COMPLETED = "COMPLETED", "Completed"


class RefundMethod(models.TextChoices):
    ORIGINAL_SOURCE = "ORIGINAL_SOURCE", "Original Payment Method"
    WALLET_CREDIT = "WALLET_CREDIT", "LocalHub Wallet Credit"


class RefundRequest(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    refund_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique refund reference identifier (e.g. REF-2026-1001).",
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refund_requests",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="refund_requests",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    reason = models.TextField()
    refund_method = models.CharField(
        max_length=20,
        choices=RefundMethod.choices,
        default=RefundMethod.WALLET_CREDIT,
    )
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_refunds",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    admin_notes = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "payments_refund_request"
        ordering = ["-created_at"]
        verbose_name = "Refund Request"
        verbose_name_plural = "Refund Requests"

    def __str__(self):
        return f"{self.refund_reference} (₹{self.amount}) - {self.customer.email} [{self.status}]"
