from rest_framework.permissions import BasePermission
from .models import BookingStatus


class IsBookingOwner(BasePermission):
    message = "You do not have permission to access this booking."

    def has_object_permission(self, request, view, obj):
        return obj.customer == request.user


class CanUpdateBooking(BasePermission):

    message = "This booking cannot be updated."

    def has_object_permission(self, request, view, obj):
        return (
            obj.customer == request.user
            and obj.status in [
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            ]
        )


class CanCancelBooking(BasePermission):

    message = "This booking cannot be cancelled."

    def has_object_permission(self, request, view, obj):

        return (
            obj.customer == request.user
            and obj.status in [
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.WORKER_ASSIGNED,
            ]
        )


class CanCancelBooking(BasePermission):

    message = "This booking cannot be cancelled."

    def has_object_permission(self, request, view, obj):

        return (
            obj.customer == request.user
            and obj.status in [
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.WORKER_ASSIGNED,
            ]
        )