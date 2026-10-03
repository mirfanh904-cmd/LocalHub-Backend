from .models import Notification


class NotificationSelector:

    @staticmethod
    def user_notifications(user):
        return Notification.objects.filter(user=user).order_by("-created_at")

    @staticmethod
    def unread_count(user):
        if not user.is_authenticated:
            return 0
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def recent_activities(user):
        activities = []
        from bookings.models import BookingStatusHistory, Review
        
        # Fetch recent booking history status changes
        history_items = BookingStatusHistory.objects.filter(
            booking__customer=user
        ).select_related("booking", "booking__service").order_by("-created_at")[:10]
        
        for item in history_items:
            status_display = item.get_status_display()
            # Map status to icon
            icon = "bi-bell"
            if item.status == "pending":
                icon = "bi-hourglass"
            elif item.status == "confirmed":
                icon = "bi-check-circle"
            elif item.status == "worker_assigned":
                icon = "bi-person-check"
            elif item.status == "on_the_way":
                icon = "bi-truck"
            elif item.status == "arrived":
                icon = "bi-geo-alt"
            elif item.status == "started":
                icon = "bi-play-circle"
            elif item.status == "in_progress":
                icon = "bi-tools"
            elif item.status == "completed":
                icon = "bi-patch-check"
            elif item.status == "cancelled":
                icon = "bi-x-circle"

            activities.append({
                "type": "status_change",
                "title": f"Booking {status_display}",
                "detail": f"{item.booking.service.name} (#{item.booking.booking_number})",
                "created_at": item.created_at,
                "icon": icon,
            })
            
        # Fetch reviews
        reviews = Review.objects.filter(
            customer=user
        ).select_related("booking", "service").order_by("-created_at")[:10]
        
        for rev in reviews:
            activities.append({
                "type": "review_submitted",
                "title": "Review Submitted",
                "detail": f"Rated {rev.rating} stars for {rev.service.name} (#{rev.booking.booking_number})",
                "created_at": rev.created_at,
                "icon": "bi-star-fill",
            })
            
        # Sort combined list by created_at descending
        activities.sort(key=lambda x: x["created_at"], reverse=True)
        return activities[:10]
