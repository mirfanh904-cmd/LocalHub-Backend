import re
import secrets
from decimal import Decimal
from datetime import datetime, timedelta
from services.services.services import ServiceRequirementService
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError

from .models import (
    Booking,
    BookingStatus,
    BookingStatusHistory,
    BookingOTP,
    BookingRescheduleRequest,
    RescheduleStatus,
)
from .validators import BookingValidator

from services.services import ServiceSelector
from accounts.models import Address
from professionals.selectors import ProfessionalSelector
from accounts.models import ProfessionalService
from services.services.selectors import  PackageSelector


def parse_duration_to_timedelta(val, default_hours=2):
    if not val:
        return timedelta(hours=default_hours)
    if isinstance(val, timedelta):
        return val
    if isinstance(val, (int, float)):
        return timedelta(minutes=float(val))
    
    val_str = str(val).strip().lower()
    
    hour_match = re.search(r'([\d\.]+)\s*(?:hours?|hrs?|h\b)', val_str)
    min_match = re.search(r'([\d\.]+)\s*(?:minutes?|mins?|m\b)', val_str)
    
    if hour_match or min_match:
        hours = float(hour_match.group(1)) if hour_match else 0.0
        minutes = float(min_match.group(1)) if min_match else 0.0
        return timedelta(hours=hours, minutes=minutes)
        
    if ":" in val_str:
        parts = val_str.split(":")
        try:
            if len(parts) == 3:
                return timedelta(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))
            elif len(parts) == 2:
                return timedelta(hours=int(parts[0]), minutes=int(parts[1]))
        except ValueError:
            pass

    try:
        num = float(val_str)
        if num <= 24:
            return timedelta(hours=num)
        return timedelta(minutes=num)
    except ValueError:
        pass

    return timedelta(hours=default_hours)


class BookingService:

    @staticmethod
    def generate_booking_number():

        year = timezone.now().year

        last_booking = (
            Booking.objects
            .filter(booking_number__startswith=f"LH-{year}-")
            .order_by("-id")
            .first()
        )

        if last_booking:

            last_number = int(last_booking.booking_number.split("-")[-1])

        else:

            last_number = 0

        return f"LH-{year}-{last_number + 1:06d}"

    @staticmethod
    def calculate_total(subtotal, discount=0, platform_fee=0, tax=0):

        subtotal = Decimal(subtotal)
        discount = Decimal(discount)
        platform_fee = Decimal(platform_fee)
        tax = Decimal(tax)

        return subtotal - discount + platform_fee + tax

    @staticmethod
    @transaction.atomic
    def create(validated_data):

        BookingValidator.validate_booking(
            service=validated_data["service"],
            address=validated_data["address"],
            booking_date=validated_data["booking_date"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
        )

        validated_data["booking_number"] = (
            BookingService.generate_booking_number()
        )

        validated_data["total_amount"] = (
            BookingService.calculate_total(
                subtotal=validated_data.get("subtotal", 0),
                discount=validated_data.get("discount", 0),
                platform_fee=validated_data.get("platform_fee", 0),
                tax=validated_data.get("tax", 0),
            )
        )

        worker = validated_data.get("worker", None)
        validated_data.setdefault("status", BookingStatus.PENDING)
        if worker:
            history_note = f"Booking created with selected professional: {getattr(worker, 'full_name', str(worker))}."
        else:
            history_note = "Booking created. Awaiting professional assignment by LocalHub."

        booking = Booking.objects.create(**validated_data)

        BookingStatusHistory.objects.create(
            booking=booking,
            status=booking.status,
            changed_by=booking.customer,
            source="system",
            note=history_note,
        )

        from notifications.services import NotificationService
        NotificationService.trigger_status_change_notifications(booking, booking.status)

        return booking

    @staticmethod
    @transaction.atomic
    def update(booking, validated_data):

        for field, value in validated_data.items():

            setattr(booking, field, value)

        BookingValidator.validate_booking(
            service=booking.service,
            address=booking.address,
            booking_date=booking.booking_date,
            start_time=booking.start_time,
            end_time=booking.end_time,
        )

        booking.total_amount = (
            BookingService.calculate_total(
                subtotal=booking.subtotal,
                discount=booking.discount,
                platform_fee=booking.platform_fee,
                tax=booking.tax,
            )
        )

        booking.save()

        return booking

    @staticmethod
    @transaction.atomic
    def change_status(
        booking,
        status,
        changed_by=None,
        source="system",
        note="",
    ):

        BookingValidator.validate_status_transition(
            booking.status,
            status,
        )

        booking.status = status

        booking.status_updated_at = timezone.now()

        if status == BookingStatus.CANCELLED:

            booking.cancelled_at = timezone.now()

        if status == BookingStatus.COMPLETED:

            booking.completed_at = timezone.now()

        booking.save(
            update_fields=[
                "status",
                "status_updated_at",
                "cancelled_at",
                "completed_at",
            ]
        )

        BookingStatusHistory.objects.create(
            booking=booking,
            status=status,
            changed_by=changed_by,
            source=source,
            note=note,
        )

        if status == BookingStatus.COMPLETED:
            try:
                from payments.services import EscrowService
                EscrowService.release_booking_escrow(booking)
            except Exception:
                pass

        from notifications.services import NotificationService
        NotificationService.trigger_status_change_notifications(booking, status)

        return booking

    @staticmethod
    @transaction.atomic
    def assign_worker(
        booking,
        worker,
        changed_by=None,
    ):
        BookingValidator.validate_worker_assignment(worker)

        # Concurrency protection using select_for_update()
        locked_booking = Booking.objects.select_for_update().get(id=booking.id)
        if locked_booking.worker is not None and locked_booking.worker != worker:
            raise ValidationError("This booking is already assigned to another professional.")

        if locked_booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            raise ValidationError(f"Cannot assign worker to a booking in {locked_booking.status} status.")

        locked_booking.worker = worker
        locked_booking.save(update_fields=["worker"])

        source = "admin" if changed_by and (getattr(changed_by, 'is_staff', False) or getattr(changed_by, 'role', '') == 'ADMIN') else "worker"

        return BookingService.change_status(
            booking=locked_booking,
            status=BookingStatus.WORKER_ASSIGNED,
            changed_by=changed_by,
            source=source,
            note="Worker assigned.",
        )

    @staticmethod
    def confirm(
            booking,
            changed_by=None,
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.CONFIRMED,
            changed_by=changed_by,
            source="system",
            note="Booking confirmed.",
        )

    @staticmethod
    def on_the_way(
            booking,
            changed_by=None,
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.ON_THE_WAY,
            changed_by=changed_by,
            source="worker",
            note="Professional is on the way.",
        )

    @staticmethod
    def arrived(
            booking,
            changed_by=None,
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.ARRIVED,
            changed_by=changed_by,
            source="worker",
            note="Professional arrived.",
        )

    @staticmethod
    def started(
            booking,
            changed_by=None,
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.STARTED,
            changed_by=changed_by,
            source="worker",
            note="Service started.",
        )



    @staticmethod
    def in_progress(
            booking,
            changed_by=None,
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.IN_PROGRESS,
            changed_by=changed_by,
            source="worker",
            note="Service in progress.",
        )



    @staticmethod
    @transaction.atomic
    def cancel(
        booking,
        changed_by=None,
        cancelled_reason="",
        source="customer",
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.CANCELLED,
            changed_by=changed_by,
            source=source,
            note=cancelled_reason or "Booking cancelled.",
        )

    @staticmethod
    @transaction.atomic
    def complete(
        booking,
        changed_by=None,
    ):

        return BookingService.change_status(
            booking=booking,
            status=BookingStatus.COMPLETED,
            changed_by=changed_by,
            source="worker",
            note="Booking completed.",
        )


class BookingOTPService:

    @staticmethod
    def generate_otp_digits(length=6):
        return "".join(secrets.choice("0123456789") for _ in range(length))

    @staticmethod
    @transaction.atomic
    def generate_otp(booking, expiry_minutes=15):
        locked_booking = Booking.objects.select_for_update().get(id=booking.id)
        if locked_booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            raise ValidationError("Cannot generate OTP for a completed or cancelled booking.")

        raw_otp = BookingOTPService.generate_otp_digits(6)
        hashed_otp = make_password(raw_otp)
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

        otp_obj, created = BookingOTP.objects.get_or_create(
            booking=locked_booking,
            defaults={
                "otp_hash": hashed_otp,
                "expires_at": expires_at,
                "attempts": 0,
                "max_attempts": 3,
                "is_verified": False,
                "locked_until": None,
            },
        )
        if not created:
            otp_obj.otp_hash = hashed_otp
            otp_obj.expires_at = expires_at
            otp_obj.attempts = 0
            otp_obj.is_verified = False
            otp_obj.verified_at = None
            otp_obj.locked_until = None
            otp_obj.save()

        from notifications.services import NotificationService
        NotificationService.trigger_otp_generated(locked_booking, raw_otp)

        return raw_otp

    @staticmethod
    def verify_otp(booking, entered_otp, verified_by=None):
        try:
            otp_obj = BookingOTP.objects.get(booking_id=booking.id)
        except BookingOTP.DoesNotExist:
            raise ValidationError("No OTP found for this booking. Please generate a new OTP.")

        if otp_obj.is_verified:
            raise ValidationError("OTP has already been verified for this booking.")

        now = timezone.now()
        if otp_obj.locked_until and now < otp_obj.locked_until:
            minutes_left = max(1, int((otp_obj.locked_until - now).total_seconds() / 60))
            raise ValidationError(
                f"Verification is temporarily locked due to maximum failed attempts. Please try again in {minutes_left} minute(s)."
            )

        if now > otp_obj.expires_at:
            raise ValidationError("OTP has expired. Please request a new OTP.")

        if not entered_otp or not str(entered_otp).strip():
            raise ValidationError("Please provide a valid 6-digit OTP.")

        is_match = check_password(str(entered_otp).strip(), otp_obj.otp_hash)

        if not is_match:
            otp_obj.attempts += 1
            if otp_obj.attempts >= otp_obj.max_attempts:
                otp_obj.locked_until = now + timedelta(minutes=15)
                otp_obj.save(update_fields=["attempts", "locked_until", "updated_at"])
                raise ValidationError("Maximum failed attempts reached. Verification locked for 15 minutes.")

            otp_obj.save(update_fields=["attempts", "updated_at"])
            remaining = otp_obj.max_attempts - otp_obj.attempts
            raise ValidationError(f"Invalid OTP. {remaining} attempt(s) remaining.")

        with transaction.atomic():
            locked_booking = Booking.objects.select_for_update().get(id=booking.id)
            otp_obj = BookingOTP.objects.select_for_update().get(id=otp_obj.id)
            otp_obj.is_verified = True
            otp_obj.verified_at = now
            otp_obj.attempts = 0
            otp_obj.locked_until = None
            otp_obj.save(update_fields=["is_verified", "verified_at", "attempts", "locked_until", "updated_at"])

            BookingStatusHistory.objects.create(
                booking=locked_booking,
                status=locked_booking.status,
                changed_by=verified_by,
                source="worker" if verified_by == locked_booking.worker else "system",
                note="OTP verified successfully for service initiation.",
            )

            from notifications.services import NotificationService
            NotificationService.trigger_otp_verified(locked_booking)

            if locked_booking.status == BookingStatus.ARRIVED:
                BookingService.change_status(
                    booking=locked_booking,
                    status=BookingStatus.STARTED,
                    changed_by=verified_by,
                    source="worker",
                    note="Service started after OTP verification.",
                )

        return True

    @staticmethod
    def get_otp_status(booking):
        try:
            otp_obj = BookingOTP.objects.get(booking=booking)
            now = timezone.now()
            is_locked = bool(otp_obj.locked_until and now < otp_obj.locked_until)
            is_expired = bool(not otp_obj.is_verified and now > otp_obj.expires_at)
            return {
                "is_generated": True,
                "is_verified": otp_obj.is_verified,
                "verified_at": otp_obj.verified_at,
                "expires_at": otp_obj.expires_at,
                "is_expired": is_expired,
                "is_locked": is_locked,
                "locked_until": otp_obj.locked_until,
                "attempts": otp_obj.attempts,
                "max_attempts": otp_obj.max_attempts,
            }
        except BookingOTP.DoesNotExist:
            return {
                "is_generated": False,
                "is_verified": False,
                "verified_at": None,
                "expires_at": None,
                "is_expired": False,
                "is_locked": False,
                "locked_until": None,
                "attempts": 0,
                "max_attempts": 3,
            }


class BookingRescheduleService:

    @staticmethod
    @transaction.atomic
    def create_request(
        booking,
        requested_by,
        requested_date,
        requested_start_time,
        requested_end_time,
        reason="",
    ):
        locked_booking = Booking.objects.select_for_update().get(id=booking.id)

        if locked_booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            raise ValidationError(f"Cannot reschedule a booking in {locked_booking.status} status.")

        if locked_booking.status in [BookingStatus.STARTED, BookingStatus.IN_PROGRESS]:
            raise ValidationError("Cannot reschedule a booking that is currently in progress.")

        # Check existing active request
        existing_pending = BookingRescheduleRequest.objects.filter(
            booking=locked_booking,
            status=RescheduleStatus.PENDING,
        ).exists()
        if existing_pending:
            raise ValidationError("A pending reschedule request already exists for this booking.")

        # Validate date and times
        if requested_date < timezone.localdate():
            raise ValidationError("Requested booking date cannot be in the past.")

        if requested_start_time >= requested_end_time:
            raise ValidationError("Requested end time must be after start time.")

        reschedule_request = BookingRescheduleRequest.objects.create(
            booking=locked_booking,
            requested_by=requested_by,
            original_date=locked_booking.booking_date,
            original_start_time=locked_booking.start_time,
            original_end_time=locked_booking.end_time,
            requested_date=requested_date,
            requested_start_time=requested_start_time,
            requested_end_time=requested_end_time,
            reason=reason.strip() if reason else "",
            status=RescheduleStatus.PENDING,
        )

        source = "customer" if requested_by == locked_booking.customer else "worker"
        BookingStatusHistory.objects.create(
            booking=locked_booking,
            status=locked_booking.status,
            changed_by=requested_by,
            source=source,
            note=f"Reschedule requested to {requested_date} ({requested_start_time} - {requested_end_time}). Reason: {reason or 'None'}",
        )

        from notifications.services import NotificationService
        NotificationService.trigger_reschedule_requested(locked_booking, reschedule_request)

        return reschedule_request

    @staticmethod
    @transaction.atomic
    def respond_request(reschedule_request, user, action, response_note=""):
        req = BookingRescheduleRequest.objects.select_for_update().get(id=reschedule_request.id)
        if req.status != RescheduleStatus.PENDING:
            raise ValidationError("This reschedule request is no longer pending.")

        booking = Booking.objects.select_for_update().get(id=req.booking_id)
        is_customer = user == booking.customer
        is_worker = user == booking.worker
        is_admin = getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN"

        if req.requested_by == user and not is_admin:
            raise ValidationError("You cannot respond to your own reschedule request. You can only cancel it.")

        if not (is_customer or is_worker or is_admin):
            raise ValidationError("You are not authorized to respond to this reschedule request.")

        action = str(action).lower().strip()
        now = timezone.now()

        if action == "accept":
            req.status = RescheduleStatus.ACCEPTED
            req.responded_by = user
            req.response_note = response_note.strip() if response_note else ""
            req.responded_at = now
            req.save()

            booking.booking_date = req.requested_date
            booking.start_time = req.requested_start_time
            booking.end_time = req.requested_end_time
            booking.save(update_fields=["booking_date", "start_time", "end_time", "updated_at"])

            source = "worker" if is_worker else ("customer" if is_customer else "admin")
            BookingStatusHistory.objects.create(
                booking=booking,
                status=booking.status,
                changed_by=user,
                source=source,
                note=f"Reschedule accepted. New schedule: {booking.booking_date} ({booking.start_time} - {booking.end_time}).",
            )

            from notifications.services import NotificationService
            NotificationService.trigger_reschedule_responded(booking, req, accepted=True)

        elif action == "reject":
            req.status = RescheduleStatus.REJECTED
            req.responded_by = user
            req.response_note = response_note.strip() if response_note else ""
            req.responded_at = now
            req.save()

            source = "worker" if is_worker else ("customer" if is_customer else "admin")
            BookingStatusHistory.objects.create(
                booking=booking,
                status=booking.status,
                changed_by=user,
                source=source,
                note=f"Reschedule request rejected. Note: {response_note or 'None'}",
            )

            from notifications.services import NotificationService
            NotificationService.trigger_reschedule_responded(booking, req, accepted=False)
        else:
            raise ValidationError("Invalid action. Must be 'accept' or 'reject'.")

        return req

    @staticmethod
    @transaction.atomic
    def cancel_request(reschedule_request, user):
        req = BookingRescheduleRequest.objects.select_for_update().get(id=reschedule_request.id)
        if req.status != RescheduleStatus.PENDING:
            raise ValidationError("Only pending reschedule requests can be cancelled.")

        is_creator = req.requested_by == user
        is_admin = getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN"
        if not (is_creator or is_admin):
            raise ValidationError("You can only cancel your own reschedule requests.")

        req.status = RescheduleStatus.CANCELLED
        req.response_note = "Cancelled by requester."
        req.responded_at = timezone.now()
        req.save()

        return req


    @staticmethod
    @transaction.atomic
    def create_booking(request, slug):

        service = ServiceSelector.get_by_slug(slug)

        if not service:
            raise ValueError("Invalid service.")
        requirements = (
            ServiceRequirementService.extract_and_validate(
                service,
                request.POST,
            )
        )
        address = Address.objects.get(
            id=request.POST.get("address"),
            user=request.user,
        )

        professional = None

        professional_id = request.POST.get("professional")

        if professional_id:
            professional = ProfessionalSelector.detail(
                professional_id,
            )

        package = None

        package_slug = request.POST.get("package")

        if package_slug:
            package = PackageSelector.detail(package_slug)

        start_time = datetime.strptime(
            request.POST.get("start_time"),
            "%H:%M",
        )

        booking_date = datetime.strptime(
            request.POST.get("booking_date"),
            "%Y-%m-%d",
        ).date()

        professional_service = None

        if professional:
            professional_service = (
                ProfessionalSelector.professional_service(
                    professional.user_id,
                    service,
                )
            )

        if package:

            subtotal = package.price

        elif (
                professional_service
                and professional_service.custom_price
        ):

            subtotal = professional_service.custom_price

        elif (
                professional
                and professional.minimum_charge
        ):

            subtotal = professional.minimum_charge

        else:

            subtotal = service.starting_price

        if (
                professional_service
                and professional_service.estimated_duration
        ):

            duration = parse_duration_to_timedelta(professional_service.estimated_duration)

        elif package and package.duration:

            duration = parse_duration_to_timedelta(package.duration)

        elif service.estimated_duration:

            duration = parse_duration_to_timedelta(service.estimated_duration)

        else:

            duration = timedelta(hours=2)

        end_time = start_time + duration

        booking = BookingService.create(
            {
                "customer": request.user,
                "worker": professional.user if professional else None,
                "service": service,
                "package": package,
                "package_price": package.price if package else Decimal("0.00"),
                "address": address,
                "booking_date": booking_date,
                "start_time": start_time.time(),
                "end_time": end_time.time(),
                "estimated_duration": duration,
                "subtotal": subtotal,
                "discount": Decimal("0.00"),
                "platform_fee": Decimal("0.00"),
                "tax": Decimal("0.00"),
                "customer_note": request.POST.get(
                    "customer_note",
                    "",),
                "requirements": requirements,

            }
        )

        return booking


class ReviewService:

    @staticmethod
    @transaction.atomic
    def create_review(booking, customer, rating, comment=""):
        from bookings.models import BookingStatus, Review
        from django.db.models import Avg, Count
        
        # 1. Validations
        if booking.customer != customer:
            raise ValueError("You are not authorized to review this booking.")
        if booking.status != BookingStatus.COMPLETED:
            raise ValueError("Only completed bookings can be reviewed.")
        if booking.is_reviewed:
            raise ValueError("This booking has already been reviewed.")
        if not (1 <= int(rating) <= 5):
            raise ValueError("Rating must be between 1 and 5.")
            
        # 2. Create Review
        review = Review.objects.create(
            booking=booking,
            customer=customer,
            service=booking.service,
            worker=booking.worker,
            rating=int(rating),
            comment=comment
        )
        
        # 3. Update Booking is_reviewed status
        booking.is_reviewed = True
        booking.save(update_fields=["is_reviewed"])
        
        # 4. Recalculate Service Ratings
        service = booking.service
        stats = Review.objects.filter(service=service).aggregate(
            avg_rating=Avg("rating"),
            count=Count("id")
        )
        service.average_rating = stats["avg_rating"] or Decimal("0.00")
        service.reviews_count = stats["count"] or 0
        service.save(update_fields=["average_rating", "reviews_count"])
        
        # 5. Recalculate ProfessionalProfile Ratings
        if booking.worker:
            profile = getattr(booking.worker, "professional_profile", None)
            if profile:
                w_stats = Review.objects.filter(worker=booking.worker).aggregate(
                    avg_rating=Avg("rating"),
                    count=Count("id")
                )
                profile.average_rating = w_stats["avg_rating"] or Decimal("0.00")
                profile.reviews_count = w_stats["count"] or 0
                profile.save(update_fields=["average_rating", "reviews_count"])
                
        # 6. Trigger review notification to the professional
        from notifications.services import NotificationService
        NotificationService.trigger_review_submitted(booking, review)
        
        return review


class ReviewReplyService:

    @staticmethod
    @transaction.atomic
    def reply_to_review(review, professional_user, comment):
        from bookings.models import ReviewReply
        from django.core.exceptions import ValidationError

        if not comment or not comment.strip():
            raise ValidationError("Reply comment cannot be empty.")

        # Ensure the user is the assigned worker on the booking
        if review.worker != professional_user and getattr(review.booking, "worker", None) != professional_user:
            raise ValidationError("You can only reply to reviews on bookings assigned to you.")

        reply, created = ReviewReply.objects.get_or_create(
            review=review,
            defaults={
                "professional": professional_user,
                "comment": comment.strip(),
            }
        )
        if not created:
            reply.comment = comment.strip()
            reply.save(update_fields=["comment", "updated_at"])

        return reply

    @staticmethod
    @transaction.atomic
    def delete_reply(reply, user):
        from django.core.exceptions import ValidationError
        if reply.professional != user and not getattr(user, "is_staff", False) and getattr(user, "role", "") != "ADMIN":
            raise ValidationError("You are not authorized to delete this review reply.")
        reply.delete()


class ReviewReportService:

    @staticmethod
    @transaction.atomic
    def report_review(review, reporter_user, reason, description=""):
        from bookings.models import ReviewReport
        from django.core.exceptions import ValidationError

        if review.customer == reporter_user:
            raise ValidationError("You cannot report your own review.")

        if ReviewReport.objects.filter(review=review, reporter=reporter_user).exists():
            raise ValidationError("You have already reported this review.")

        report = ReviewReport.objects.create(
            review=review,
            reporter=reporter_user,
            reason=reason,
            description=description.strip() if description else "",
        )
        return report

    @staticmethod
    @transaction.atomic
    def moderate_report(report, admin_user, status, admin_notes=""):
        report.status = status
        report.admin_notes = admin_notes
        report.reviewed_by = admin_user
        report.reviewed_at = timezone.now()
        report.save(update_fields=["status", "admin_notes", "reviewed_by", "reviewed_at", "updated_at"])
        return report


class ComplaintService:

    @staticmethod
    def generate_complaint_number():
        year = timezone.now().year
        from bookings.models import Complaint
        last_complaint = (
            Complaint.objects
            .filter(complaint_number__startswith=f"CMP-{year}-")
            .order_by("-id")
            .first()
        )
        if last_complaint:
            last_number = int(last_complaint.complaint_number.split("-")[-1])
        else:
            last_number = 0
        return f"CMP-{year}-{last_number + 1:06d}"

    @staticmethod
    @transaction.atomic
    def create_complaint(customer, category, subject, description, booking=None, priority="medium"):
        from bookings.models import Complaint, ComplaintPriority
        from django.core.exceptions import ValidationError

        if not subject or not subject.strip():
            raise ValidationError("Subject is required.")
        if not description or not description.strip():
            raise ValidationError("Description is required.")

        professional = None
        if booking:
            if booking.customer != customer:
                raise ValidationError("You can only file complaints against your own bookings.")
            professional = booking.worker

        complaint = Complaint.objects.create(
            complaint_number=ComplaintService.generate_complaint_number(),
            customer=customer,
            booking=booking,
            professional=professional,
            category=category,
            subject=subject.strip(),
            description=description.strip(),
            priority=priority if priority in ComplaintPriority.values else ComplaintPriority.MEDIUM,
        )
        return complaint

    @staticmethod
    @transaction.atomic
    def investigate_complaint(complaint, admin_user, admin_notes=""):
        from bookings.models import ComplaintStatus
        complaint.status = ComplaintStatus.UNDER_INVESTIGATION
        if admin_notes:
            complaint.admin_notes = admin_notes
        complaint.save(update_fields=["status", "admin_notes", "updated_at"])
        return complaint

    @staticmethod
    @transaction.atomic
    def resolve_complaint(complaint, admin_user, resolution, admin_notes=""):
        from bookings.models import ComplaintStatus
        from django.core.exceptions import ValidationError
        if not resolution or not resolution.strip():
            raise ValidationError("A resolution description is required.")

        complaint.status = ComplaintStatus.RESOLVED
        complaint.resolution = resolution.strip()
        if admin_notes:
            complaint.admin_notes = admin_notes
        complaint.resolved_by = admin_user
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=["status", "resolution", "admin_notes", "resolved_by", "resolved_at", "updated_at"])
        return complaint

    @staticmethod
    @transaction.atomic
    def reject_complaint(complaint, admin_user, reason, admin_notes=""):
        from bookings.models import ComplaintStatus
        from django.core.exceptions import ValidationError
        if not reason or not reason.strip():
            raise ValidationError("A reason for rejection is required.")

        complaint.status = ComplaintStatus.REJECTED
        complaint.resolution = f"Rejected: {reason.strip()}"
        if admin_notes:
            complaint.admin_notes = admin_notes
        complaint.resolved_by = admin_user
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=["status", "resolution", "admin_notes", "resolved_by", "resolved_at", "updated_at"])
        return complaint