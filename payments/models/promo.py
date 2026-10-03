import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from common.models import BaseModel


class PromoDiscountType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage Discount"
    FIXED = "FIXED", "Fixed Amount Discount"


class PromoCode(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )
    description = models.TextField(
        blank=True,
    )
    discount_type = models.CharField(
        max_length=20,
        choices=PromoDiscountType.choices,
        default=PromoDiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage (e.g. 15.00 for 15%) or fixed amount (e.g. 100.00)",
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount cap for percentage discounts",
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Minimum subtotal required to apply this code",
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
    )
    valid_until = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(
        default=100,
        help_text="Maximum total times this code can be redeemed",
    )
    used_count = models.PositiveIntegerField(
        default=0,
    )
    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "payments_promo_code"
        ordering = ["-created_at"]
        verbose_name = "Promo Code"
        verbose_name_plural = "Promo Codes"

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()} - {self.discount_value})"

    def is_valid(self, subtotal: Decimal) -> tuple[bool, str]:
        now = timezone.now()
        if not self.is_active:
            return False, "Promo code is inactive."
        if now < self.valid_from:
            return False, "Promo code is not yet active."
        if now > self.valid_until:
            return False, "Promo code has expired."
        if self.used_count >= self.usage_limit:
            return False, "Promo code usage limit has been reached."
        if subtotal < self.min_order_amount:
            return False, f"Minimum order subtotal of ₹{self.min_order_amount} required."
        return True, ""

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        valid, _ = self.is_valid(subtotal)
        if not valid:
            return Decimal("0.00")
        if self.discount_type == PromoDiscountType.PERCENTAGE:
            discount = (subtotal * self.discount_value / Decimal("100.00")).quantize(Decimal("0.01"))
            if self.max_discount_amount and discount > self.max_discount_amount:
                discount = self.max_discount_amount
            return discount
        elif self.discount_type == PromoDiscountType.FIXED:
            return min(self.discount_value, subtotal)
        return Decimal("0.00")
