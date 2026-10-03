from bookings.models import Booking, BookingStatus
from accounts.models import Address


class DashboardSelector:

    @staticmethod
    def customer_dashboard(user):

        total_bookings = Booking.objects.filter(
            customer=user,
        ).count()

        upcoming_bookings = Booking.objects.filter(
            customer=user,
            status__in=[
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.WORKER_ASSIGNED,
                BookingStatus.ON_THE_WAY,
                BookingStatus.ARRIVED,
                BookingStatus.STARTED,
                BookingStatus.IN_PROGRESS,
            ],
        ).count()

        completed_bookings = Booking.objects.filter(
            customer=user,
            status=BookingStatus.COMPLETED,
        ).count()

        cancelled_bookings = Booking.objects.filter(
            customer=user,
            status=BookingStatus.CANCELLED,
        ).count()

        upcoming_booking = (
            Booking.objects
            .select_related(
                "service",
                "worker",
                "worker__professional_profile",
                "address",
                "package",
            )
            .filter(
                customer=user,
                status__in=[
                    BookingStatus.PENDING,
                    BookingStatus.CONFIRMED,
                    BookingStatus.WORKER_ASSIGNED,
                    BookingStatus.ON_THE_WAY,
                    BookingStatus.ARRIVED,
                    BookingStatus.STARTED,
                    BookingStatus.IN_PROGRESS,
                ],
            )
            .order_by(
                "booking_date",
                "start_time",
            )
            .first()
        )

        recent_bookings = (
            Booking.objects
            .select_related(
                "service",
                "worker",
                "package",
            )
            .filter(
                customer=user,
            )
            .order_by("-created_at")[:5]
        )

        addresses = (
            Address.objects
            .filter(
                user=user,
            )[:3]
        )

        from services.models import Service
        from accounts.models import FavouriteService, FavouriteProfessional
        from notifications.selectors import NotificationSelector

        recommended_services = Service.objects.filter(is_active=True).order_by(
            "-is_featured", "-average_rating", "-reviews_count"
        )[:4]

        fav_services = FavouriteService.objects.filter(user=user).select_related("service")[:4]
        fav_professionals = FavouriteProfessional.objects.filter(user=user).select_related(
            "professional", "professional__user"
        )[:4]

        unread_notifications_count = NotificationSelector.unread_count(user)
        recent_notifications = NotificationSelector.user_notifications(user)[:5]
        recent_activities = NotificationSelector.recent_activities(user)

        return {

            "total_bookings": total_bookings,

            "upcoming_bookings": upcoming_bookings,

            "completed_bookings": completed_bookings,

            "cancelled_bookings": cancelled_bookings,

            "upcoming_booking": upcoming_booking,

            "recent_bookings": recent_bookings,

            "addresses": addresses,

            "recommended_services": recommended_services,

            "favourite_services": fav_services,

            "favourite_professionals": fav_professionals,

            "unread_notifications_count": unread_notifications_count,

            "recent_notifications": recent_notifications,

            "recent_activities": recent_activities,

        }


class AdminDashboardSelector:

    @staticmethod
    def get_statistics():
        from django.utils import timezone
        from django.db.models import Sum
        from accounts.models import User, ProfessionalProfile
        from services.models import Category, Service

        today = timezone.localdate()

        from verification.models import ProfessionalVerification, VerificationStatus

        total_users = User.objects.count()
        total_professionals = ProfessionalProfile.objects.count()
        pending_approvals = ProfessionalVerification.objects.filter(status=VerificationStatus.PENDING).count()
        total_categories = Category.objects.count()
        total_services = Service.objects.count()

        pending_bookings = Booking.objects.filter(status=BookingStatus.PENDING).count()
        today_bookings = Booking.objects.filter(booking_date=today).count()

        revenue_res = Booking.objects.filter(status=BookingStatus.COMPLETED).aggregate(Sum("total_amount"))
        total_revenue = revenue_res.get("total_amount__sum") or 0.00

        return {
            "total_users": total_users,
            "total_professionals": total_professionals,
            "pending_approvals": pending_approvals,
            "total_categories": total_categories,
            "total_services": total_services,
            "pending_bookings": pending_bookings,
            "today_bookings": today_bookings,
            "total_revenue": total_revenue,
        }