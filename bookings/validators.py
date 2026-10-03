from django.utils import timezone

from .models import BookingStatus


class BookingValidator:

    @staticmethod
    def validate_booking_date(booking_date):

        if booking_date < timezone.localdate():

            raise ValueError(
                "Booking date cannot be in the past."
            )

    @staticmethod
    def validate_time_slot(start_time, end_time):

        if start_time >= end_time:

            raise ValueError(
                "End time must be after start time."
            )

    @staticmethod
    def validate_service(service):

        if not service.is_active:

            raise ValueError(
                "This service is not available."
            )

    @staticmethod
    def validate_address(address):

        if not address.is_active:

            raise ValueError(
                "Selected address is inactive."
            )

    @staticmethod
    def validate_worker_assignment(worker):

        if worker is None:

            raise ValueError(
                "Worker is required."
            )

    @staticmethod
    def validate_status_transition(current_status, new_status):

        transitions = {
            BookingStatus.PENDING: [
                BookingStatus.CONFIRMED,
                BookingStatus.WORKER_ASSIGNED,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.CONFIRMED: [
                BookingStatus.WORKER_ASSIGNED,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.WORKER_ASSIGNED: [
                BookingStatus.ON_THE_WAY,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.ON_THE_WAY: [
                BookingStatus.ARRIVED,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.ARRIVED: [
                BookingStatus.STARTED,
                BookingStatus.IN_PROGRESS,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.STARTED: [
                BookingStatus.IN_PROGRESS,
            ],
            BookingStatus.IN_PROGRESS: [
                BookingStatus.COMPLETED,
            ],
            BookingStatus.COMPLETED: [],
            BookingStatus.CANCELLED: [],
        }

        if new_status not in transitions.get(current_status, []):

            raise ValueError(
                f"Invalid status transition from {current_status} to {new_status}."
            )

    @staticmethod
    def validate_booking(service, address, booking_date, start_time, end_time):

        BookingValidator.validate_service(service)

        BookingValidator.validate_address(address)

        BookingValidator.validate_booking_date(booking_date)

        BookingValidator.validate_time_slot(
            start_time,
            end_time,
        )