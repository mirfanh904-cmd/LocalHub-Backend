import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel
from .promo import PromoCode


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash on Delivery"
    ONLINE = "ONLINE", "Online Gateway"
    WALLET = "WALLET", "Wallet Balance"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"


class Payment(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    payment_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique external/receipt identifier (e.g. PAY-2026-10001).",
    )
    idempotency_key = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="Client idempotency key for preventing duplicate payment charges.",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_made",
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.ONLINE,
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    gateway_transaction_id = models.CharField(
        max_length=120,
        blank=True,
        help_text="Transaction reference returned by gateway provider.",
    )

    class Meta:
        db_table = "payments_payment"
        ordering = ["-created_at"]
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"

    def __str__(self):
        return f"{self.payment_reference} ({self.get_status_display()} - ₹{self.total_amount})"
