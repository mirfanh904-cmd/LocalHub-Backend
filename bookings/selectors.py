from django.utils import timezone
from django.db.models import Q
from .models import Booking, BookingStatus


class BookingSelector:

    @staticmethod
    def get(booking_number):

        return (
            Booking.objects
            .select_related(
                "customer",
                "worker",
                "service",
                "address",
                "package",

        )
            .filter(
                booking_number=booking_number,
            )
            .first()
        )


    @staticmethod
    def my_bookings(customer, search=None, status=None, sort="newest",):

        queryset = Booking.objects.select_related(
            "service",
            "worker",
            "address",
            "package",
        ).filter(
            customer=customer,
        )

        if search:
            queryset = queryset.filter(
                Q(booking_number__icontains=search) |
                Q(service__name__icontains=search) |
                Q(worker__first_name__icontains=search)
            )

        if status:
            queryset = queryset.filter(
                status=status,
            )
        if sort == "oldest":
            queryset = queryset.order_by("created_at")

        elif sort == "booking_date":
            queryset = queryset.order_by("booking_date", "start_time")

        else:
            queryset = queryset.order_by("-created_at")
        return queryset
    @staticmethod
    def worker_bookings(worker):

        return (
            Booking.objects
            .select_related(
                "customer",
                "service",
                "address",
                "package",
            )
            .filter(
                worker=worker,
                status__in=[
                    BookingStatus.WORKER_ASSIGNED,
                    BookingStatus.ON_THE_WAY,
                    BookingStatus.ARRIVED,
                    BookingStatus.STARTED,
                    BookingStatus.IN_PROGRESS,
                ]
            )
            .order_by("-created_at")
        )

    @staticmethod
    def pending():

        return (
            Booking.objects
            .filter(
                status=BookingStatus.PENDING,
            )
            .order_by("-created_at")
        )

    @staticmethod
    def confirmed():

        return (
            Booking.objects
            .filter(
                status=BookingStatus.CONFIRMED,
            )
            .order_by("-created_at")
        )

    @staticmethod
    def active():

        return (
            Booking.objects
            .filter(
                status__in=[
                    BookingStatus.CONFIRMED,
                    BookingStatus.WORKER_ASSIGNED,
                    BookingStatus.ON_THE_WAY,
                    BookingStatus.ARRIVED,
                    BookingStatus.STARTED,
                    BookingStatus.IN_PROGRESS,
                ]
            )
            .order_by("-created_at")
        )

    @staticmethod
    def completed():

        return (
            Booking.objects
            .filter(
                status=BookingStatus.COMPLETED,
            )
            .order_by("-completed_at")
        )

    @staticmethod
    def cancelled():

        return (
            Booking.objects
            .filter(
                status=BookingStatus.CANCELLED,
            )
            .order_by("-cancelled_at")
        )

    @staticmethod
    def today():

        return (
            Booking.objects
            .filter(
                booking_date=timezone.localdate(),
            )
            .order_by("start_time")
        )

    @staticmethod
    def upcoming():

        return (
            Booking.objects
            .filter(
                booking_date__gt=timezone.localdate(),
            )
            .order_by(
                "booking_date",
                "start_time",
            )
        )

    @staticmethod
    def recent(limit=10):

        return (
            Booking.objects
            .order_by("-created_at")[:limit]
        )

    @staticmethod
    def customer_detail(
            booking_number,
            customer,
    ):
        return (
            Booking.objects
            .select_related(
                "service",
                "worker",
                "address",
                "package",
            )
            .filter(
                booking_number=booking_number,
                customer=customer,
            )
            .first()
        )

    @staticmethod
    def history(booking):
        return booking.status_history.select_related("changed_by").all()

    @staticmethod
    def worker_today_jobs(worker):
        return (
            Booking.objects
            .select_related("customer", "service", "address", "package")
            .filter(
                worker=worker,
                booking_date=timezone.localdate(),
                status__in=[
                    BookingStatus.WORKER_ASSIGNED,
                    BookingStatus.ON_THE_WAY,
                    BookingStatus.ARRIVED,
                    BookingStatus.STARTED,
                    BookingStatus.IN_PROGRESS,
                ]
            )
            .order_by("start_time")
        )

    @staticmethod
    def worker_upcoming_jobs(worker):
        return (
            Booking.objects
            .select_related("customer", "service", "address", "package")
            .filter(
                worker=worker,
                booking_date__gt=timezone.localdate(),
                status__in=[
                    BookingStatus.WORKER_ASSIGNED,
                    BookingStatus.ON_THE_WAY,
                    BookingStatus.ARRIVED,
                    BookingStatus.STARTED,
                    BookingStatus.IN_PROGRESS,
                ]
            )
            .order_by("booking_date", "start_time")
        )

    @staticmethod
    def worker_completed_jobs(worker):
        return (
            Booking.objects
            .select_related("customer", "service", "address", "package")
            .filter(
                worker=worker,
                status=BookingStatus.COMPLETED,
            )
            .order_by("-completed_at")
        )

    @staticmethod
    def worker_earnings(worker):
        from django.db.models import Sum
        result = (
            Booking.objects
            .filter(
                worker=worker,
                status=BookingStatus.COMPLETED,
            )
            .aggregate(Sum("total_amount"))
        )
        return result.get("total_amount__sum") or 0.00

    @staticmethod
    def worker_new_requests(worker):
        return (
            Booking.objects
            .select_related("customer", "service", "address", "package")
            .filter(
                worker=worker,
                status=BookingStatus.PENDING,
            )
            .order_by("booking_date", "start_time")
        )

    @staticmethod
    def worker_cancelled_jobs(worker):
        return (
            Booking.objects
            .select_related("customer", "service", "address", "package")
            .filter(
                worker=worker,
                status=BookingStatus.CANCELLED,
            )
            .order_by("-cancelled_at")
        )

    @staticmethod
    def worker_detail(booking_number, worker):
        return (
            Booking.objects
            .select_related("customer", "service", "address", "package")
            .filter(
                booking_number=booking_number,
                worker=worker,
            )
            .first()
        )

    @staticmethod
    def worker_monthly_earnings(worker):
        from django.db.models import Sum
        from django.utils import timezone
        today = timezone.localdate()
        result = (
            Booking.objects
            .filter(
                worker=worker,
                status=BookingStatus.COMPLETED,
                completed_at__year=today.year,
                completed_at__month=today.month,
            )
            .aggregate(Sum("total_amount"))
        )
        return result.get("total_amount__sum") or 0.00