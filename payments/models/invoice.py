import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel
from .payment import Payment


class InvoiceStatus(models.TextChoices):
    ISSUED = "ISSUED", "Issued"
    PAID = "PAID", "Paid"
    REFUNDED = "REFUNDED", "Refunded"
    VOID = "VOID", "Void"


class Invoice(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Official invoice identifier (e.g. INV-2026-10001).",
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="invoice",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    recipient_name = models.CharField(
        max_length=150,
    )
    recipient_email = models.EmailField(
        blank=True,
    )
    recipient_address = models.TextField(
        blank=True,
    )
    service_summary = models.CharField(
        max_length=255,
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.ISSUED,
        db_index=True,
    )
    issued_at = models.DateTimeField(
        auto_now_add=True,
    )
    pdf_url = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        db_table = "payments_invoice"
        ordering = ["-issued_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"{self.invoice_number} - {self.recipient_name} (₹{self.total_amount})"
