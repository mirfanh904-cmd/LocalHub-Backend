from django.contrib.auth import get_user_model
from .models import Notification, NotificationType

User = get_user_model()


class NotificationService:

    @staticmethod
    def create_notification(user, notification_type, title, message, booking=None):
        if not user:
            return None
        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            booking=booking
        )

    @staticmethod
    def trigger_status_change_notifications(booking, status):
        from bookings.models import BookingStatus
        
        # 1. Booking Created / Pending
        if status == BookingStatus.PENDING:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Booking Submitted",
                message=f"Your booking {booking.booking_number} has been successfully submitted.",
                booking=booking
            )
            
        # 2. Worker Assigned (before acceptance)
        elif status == BookingStatus.WORKER_ASSIGNED:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Professional Assigned",
                message=f"A professional has been assigned to your booking {booking.booking_number}.",
                booking=booking
            )
            if booking.worker:
                NotificationService.create_notification(
                    user=booking.worker,
                    notification_type=NotificationType.BOOKING,
                    title="New Job Request",
                    message=f"You have a new job request {booking.booking_number} awaiting your response.",
                    booking=booking
                )
                
        # 3. Worker On The Way
        elif status == BookingStatus.ON_THE_WAY:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Professional On The Way",
                message=f"Your professional is on the way for booking {booking.booking_number}.",
                booking=booking
            )
            
        # 4. Worker Arrived
        elif status == BookingStatus.ARRIVED:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Professional Arrived",
                message=f"Your professional has arrived for booking {booking.booking_number}.",
                booking=booking
            )
            
        # 5. Service Started
        elif status == BookingStatus.STARTED:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Service Started",
                message=f"Your service for booking {booking.booking_number} has started.",
                booking=booking
            )
            
        # 6. Service In Progress
        elif status == BookingStatus.IN_PROGRESS:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Service In Progress",
                message=f"Your service is currently in progress for booking {booking.booking_number}.",
                booking=booking
            )
            
        # 7. Booking Completed
        elif status == BookingStatus.COMPLETED:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Booking Completed",
                message=f"Your booking {booking.booking_number} is completed. Please leave a rating and review.",
                booking=booking
            )
            if booking.worker:
                NotificationService.create_notification(
                    user=booking.worker,
                    notification_type=NotificationType.BOOKING,
                    title="Job Completed",
                    message=f"Your job {booking.booking_number} has been marked as completed. Thank you!",
                    booking=booking
                )
                
        # 8. Booking Cancelled
        elif status == BookingStatus.CANCELLED:
            NotificationService.create_notification(
                user=booking.customer,
                notification_type=NotificationType.BOOKING,
                title="Booking Cancelled",
                message=f"Your booking {booking.booking_number} has been cancelled.",
                booking=booking
            )
            if booking.worker:
                NotificationService.create_notification(
                    user=booking.worker,
                    notification_type=NotificationType.BOOKING,
                    title="Booking Cancelled",
                    message=f"Your assigned booking {booking.booking_number} has been cancelled.",
                    booking=booking
                )

    @staticmethod
    def trigger_worker_accepted(booking):
        NotificationService.create_notification(
            user=booking.customer,
            notification_type=NotificationType.BOOKING,
            title="Booking Accepted",
            message=f"The professional has accepted your booking {booking.booking_number}.",
            booking=booking
        )

    @staticmethod
    def trigger_worker_rejected(booking, worker):
        # Notify customer
        NotificationService.create_notification(
            user=booking.customer,
            notification_type=NotificationType.BOOKING,
            title="Booking Reassigned",
            message=f"The professional rejected booking {booking.booking_number}. It is returned to the pool.",
            booking=booking
        )

    @staticmethod
    def trigger_otp_generated(booking, raw_otp):
        NotificationService.create_notification(
            user=booking.customer,
            notification_type=NotificationType.BOOKING,
            title="Service Verification OTP",
            message=f"Your OTP for booking {booking.booking_number} is {raw_otp}. Share this with your professional when they arrive.",
            booking=booking,
        )

    @staticmethod
    def trigger_otp_verified(booking):
        NotificationService.create_notification(
            user=booking.customer,
            notification_type=NotificationType.BOOKING,
            title="OTP Verified — Work Started",
            message=f"Service OTP for booking {booking.booking_number} has been verified successfully.",
            booking=booking,
        )

    @staticmethod
    def trigger_reschedule_requested(booking, reschedule_request):
        recipient = booking.worker if reschedule_request.requested_by == booking.customer else booking.customer
        if recipient:
            requester_name = reschedule_request.requested_by.full_name or "Client"
            NotificationService.create_notification(
                user=recipient,
                notification_type=NotificationType.BOOKING,
                title="Reschedule Requested",
                message=f"{requester_name} requested to reschedule booking {booking.booking_number} to {reschedule_request.requested_date} at {reschedule_request.requested_start_time}.",
                booking=booking,
            )

    @staticmethod
    def trigger_reschedule_responded(booking, reschedule_request, accepted=True):
        recipient = reschedule_request.requested_by
        if recipient:
            status_text = "accepted" if accepted else "declined"
            NotificationService.create_notification(
                user=recipient,
                notification_type=NotificationType.BOOKING,
                title=f"Reschedule {status_text.capitalize()}",
                message=f"Your reschedule request for booking {booking.booking_number} was {status_text}.",
                booking=booking,
            )

    @staticmethod
    def trigger_review_submitted(booking, review):
        if booking.worker:
            NotificationService.create_notification(
                user=booking.worker,
                notification_type=NotificationType.REVIEW,
                title="New Review Received",
                message=f"You received a {review.rating}-star review for booking {booking.booking_number}.",
                booking=booking
            )

    @staticmethod
    def mark_as_read(notification_id, user):
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save(update_fields=["is_read"])
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user):
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return True
