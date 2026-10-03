from django.conf import settings
from django.db import models

from common.models import BaseModel
from services.models import Service
from accounts.models import Address


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    WORKER_ASSIGNED = "worker_assigned", "Worker Assigned"
    ON_THE_WAY = "on_the_way", "On The Way"
    ARRIVED = "arrived", "Arrived"
    STARTED = "started", "Started"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class PaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


# class Booking(BaseModel):
#
#     booking_number = models.CharField(
#         max_length=30,
#         unique=True,
#     )
#
#     customer = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="customer_bookings",
#     )
#
#     worker = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="worker_bookings",
#     )
#
#     service = models.ForeignKey(
#         Service,
#         on_delete=models.PROTECT,
#         related_name="bookings",
#     )
#
#     address = models.ForeignKey(
#         Address,
#         on_delete=models.PROTECT,
#     )
#
#     booking_date = models.DateField()
#
#     start_time = models.TimeField()
#
#     end_time = models.TimeField()
#
#     status = models.CharField(
#         max_length=30,
#         choices=BookingStatus.choices,
#         default=BookingStatus.PENDING,
#     )
#
#     payment_status = models.CharField(
#         max_length=20,
#         choices=PaymentStatus.choices,
#         default=PaymentStatus.UNPAID,
#     )
#
#     subtotal = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#     )
#
#     discount = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         default=0,
#     )
#
#     platform_fee = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         default=0,
#     )
#
#     tax = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         default=0,
#     )
#
#     total_amount = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#     )
#
#     customer_note = models.TextField(
#         blank=True,
#     )
#
#     worker_note = models.TextField(
#         blank=True,
#     )
#
#     cancelled_reason = models.TextField(
#         blank=True,
#     )
#
#     cancelled_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )
#
#     completed_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )
#
#     is_reviewed = models.BooleanField(
#         default=False,
#     )
#
#     def __str__(self):
#         return self.booking_number


class Booking(BaseModel):
    booking_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_bookings")
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="worker_bookings")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    estimated_duration = models.DurationField(null=True, blank=True,)
    status = models.CharField(max_length=30, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_note = models.TextField(blank=True)
    worker_note = models.TextField(blank=True)
    cancelled_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_reviewed = models.BooleanField(default=False)
    status_updated_at = models.DateTimeField(auto_now=True)
    package = models.ForeignKey(
        "services.ServicePackage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )

    package_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    requirements = models.JSONField(
        default=dict,
        blank=True,
        help_text="Customer answers for dynamic service requirements."
    )
    def __str__(self):

        return self.booking_number


class BookingStatusHistory(BaseModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=30, choices=BookingStatus.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=(
            ("system", "System"),
            ("customer", "Customer"),
            ("worker", "Worker"),
            ("admin", "Admin"),
        ),
        default="system",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Booking Status History"
        verbose_name_plural = "Booking Status Histories"

    def __str__(self):

        return f"{self.booking.booking_number} - {self.status}"


class Review(BaseModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE, related_name="reviews")
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews_received")
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for {self.booking.booking_number} - {self.rating} stars"


class ReviewReply(BaseModel):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="reply")
    professional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_replies")
    comment = models.TextField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Review Reply"
        verbose_name_plural = "Review Replies"

    def __str__(self):
        return f"Reply to review {self.review_id} by {self.professional}"


class ReportReason(models.TextChoices):
    SPAM = "spam", "Spam or Advertising"
    HARASSMENT = "harassment", "Harassment or Hate Speech"
    INAPPROPRIATE = "inappropriate", "Inappropriate Content"
    FAKE = "fake_review", "Fake or Fraudulent Review"
    OTHER = "other", "Other Reason"


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    REVIEWED = "reviewed", "Under Review"
    RESOLVED = "resolved", "Resolved (Action Taken)"
    DISMISSED = "dismissed", "Dismissed (No Action)"


class ReviewReport(BaseModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_reports")
    reason = models.CharField(max_length=30, choices=ReportReason.choices)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.PENDING, db_index=True)
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_review_reports")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Review Report"
        verbose_name_plural = "Review Reports"
        constraints = [
            models.UniqueConstraint(fields=["review", "reporter"], name="unique_review_report_per_user")
        ]

    def __str__(self):
        return f"Report on review {self.review_id} by {self.reporter} ({self.status})"


class ComplaintCategory(models.TextChoices):
    SERVICE_QUALITY = "service_quality", "Service Quality Issue"
    BILLING = "billing", "Billing or Payment Dispute"
    SAFETY = "safety", "Safety or Security Concern"
    MISCONDUCT = "misconduct", "Professional Misconduct"
    NO_SHOW = "no_show", "Professional Did Not Show Up"
    CANCELLATION = "cancellation", "Cancellation Dispute"
    OTHER = "other", "Other"


class ComplaintStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    UNDER_INVESTIGATION = "under_investigation", "Under Investigation"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"
    CLOSED = "closed", "Closed"


class ComplaintPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class Complaint(BaseModel):
    complaint_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    professional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints_received")
    category = models.CharField(max_length=30, choices=ComplaintCategory.choices)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=ComplaintStatus.choices, default=ComplaintStatus.PENDING, db_index=True)
    priority = models.CharField(max_length=20, choices=ComplaintPriority.choices, default=ComplaintPriority.MEDIUM)
    resolution = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_complaints")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Complaint"
        verbose_name_plural = "Complaints"

    def __str__(self):
        return f"{self.complaint_number} - {self.subject} ({self.status})"


class BookingOTP(BaseModel):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="otp",
    )
    otp_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Booking OTP"
        verbose_name_plural = "Booking OTPs"

    def __str__(self):
        return f"OTP for {self.booking.booking_number} (Verified: {self.is_verified})"


class RescheduleStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class BookingRescheduleRequest(BaseModel):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="reschedule_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reschedule_requests_made",
    )
    original_date = models.DateField()
    original_start_time = models.TimeField()
    original_end_time = models.TimeField()
    requested_date = models.DateField()
    requested_start_time = models.TimeField()
    requested_end_time = models.TimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=RescheduleStatus.choices,
        default=RescheduleStatus.PENDING,
        db_index=True,
    )
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reschedule_responses",
    )
    response_note = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Booking Reschedule Request"
        verbose_name_plural = "Booking Reschedule Requests"

    def __str__(self):
        return f"Reschedule for {self.booking.booking_number} ({self.status}) by {self.requested_by}"
