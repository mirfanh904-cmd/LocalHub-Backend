import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel
from .payment import Payment


class CommissionRecord(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="commissions",
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commission_records",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commission_records",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="commission_records",
    )
    gross_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    commission_rate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
    )
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    net_earning = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    is_settled = models.BooleanField(
        default=False,
        help_text="Whether net earning has been credited to professional available wallet balance.",
    )
    settled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "payments_commission_record"
        ordering = ["-created_at"]
        verbose_name = "Platform Commission & Earning Record"
        verbose_name_plural = "Platform Commission & Earning Records"

    def __str__(self):
        return f"Commission ₹{self.commission_amount} / Net ₹{self.net_earning} for {self.professional.email}"
