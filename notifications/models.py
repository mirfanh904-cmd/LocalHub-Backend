from django.db import models
from django.conf import settings
from common.models import BaseModel


class NotificationType(models.TextChoices):
    BOOKING = "BOOKING", "Booking"
    REVIEW = "REVIEW", "Review"
    PAYMENT = "PAYMENT", "Payment"
    VERIFICATION = "VERIFICATION", "Verification"
    SYSTEM = "SYSTEM", "System"
    PROMOTION = "PROMOTION", "Promotion"


class Notification(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications"
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        db_table = "notifications_notification"

    def __str__(self):
        return f"{self.user.email} - {self.title} ({self.notification_type})"
