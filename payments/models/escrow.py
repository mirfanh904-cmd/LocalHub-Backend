import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel
from .payment import Payment


class EscrowStatus(models.TextChoices):
    HELD = "HELD", "Funds in Escrow Vault"
    RELEASED = "RELEASED", "Released to Professional"
    REFUNDED = "REFUNDED", "Refunded to Customer"
    DISPUTED = "DISPUTED", "Locked in Dispute"


class EscrowHold(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="escrow_hold",
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escrows",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escrows",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escrows_receivable",
    )
    held_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=20,
        choices=EscrowStatus.choices,
        default=EscrowStatus.HELD,
        db_index=True,
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    release_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        db_table = "payments_escrow_hold"
        ordering = ["-created_at"]
        verbose_name = "Escrow Hold"
        verbose_name_plural = "Escrow Holds"

    def __str__(self):
        return f"Escrow ({self.get_status_display()}) - ₹{self.held_amount} for Payment {self.payment.payment_reference}"
