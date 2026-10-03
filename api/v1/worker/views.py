from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from api.permissions import IsVerifiedWorker
from bookings.models import BookingStatus, BookingStatusHistory
from bookings.selectors import BookingSelector
from bookings.services import BookingService
from notifications.services import NotificationService
from verification.trust_score_service import TrustScoreService
from api.v1.professionals.serializers import TrustScoreResponseSerializer
from .serializers import (
    WorkerBookingSerializer,
    WorkerStatusUpdateSerializer,
    WorkerRejectSerializer,
)


class WorkerBookingListAPIView(generics.ListAPIView):
    serializer_class = WorkerBookingSerializer
    permission_classes = [IsVerifiedWorker]

    @extend_schema(
        operation_id="list_worker_bookings",
        summary="List Worker Bookings",
        description="Returns a list of bookings assigned to or pending for the logged-in professional worker.",
        parameters=[
            OpenApiParameter("section", str, description="Filter by workspace section: pending, assigned, or history"),
            OpenApiParameter("status", str, description="Filter by specific booking status string"),
        ],
        responses={200: WorkerBookingSerializer(many=True)},
        tags=["Worker Operations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        section = self.request.query_params.get("section")
        status_filter = self.request.query_params.get("status")

        if section == "pending":
            return BookingSelector.worker_pending_requests(self.request.user)
        elif section == "assigned":
            return BookingSelector.worker_assigned_bookings(self.request.user)
        elif section == "history":
            return BookingSelector.worker_history_bookings(self.request.user)
        elif status_filter:
            return BookingSelector.worker_bookings(self.request.user, status=status_filter)
        return BookingSelector.worker_bookings(self.request.user)


class WorkerAcceptBookingAPIView(APIView):
    permission_classes = [IsVerifiedWorker]

    @extend_schema(
        operation_id="worker_accept_booking",
        summary="Accept Assigned Booking",
        description="Professional worker accepts a newly assigned pending booking request.",
        request=None,
        responses={
            200: OpenApiResponse(description="Booking accepted successfully"),
            400: OpenApiResponse(description="Booking cannot be accepted"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Worker Operations"],
    )
    def post(self, request, booking_number):
        booking = BookingSelector.worker_detail(booking_number, request.user)
        if not booking:
            return Response(
                {"status": "error", "message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if booking.status != BookingStatus.PENDING:
            return Response(
                {"status": "error", "message": "Only pending bookings can be accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            BookingService.change_status(
                booking=booking,
                status=BookingStatus.WORKER_ASSIGNED,
                changed_by=request.user,
                source="worker",
                note="Worker accepted the booking via API."
            )
            NotificationService.trigger_worker_accepted(booking)
            return Response(
                {"status": "success", "message": "Booking accepted successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkerRejectBookingAPIView(APIView):
    permission_classes = [IsVerifiedWorker]

    @extend_schema(
        operation_id="worker_reject_booking",
        summary="Reject Assigned Booking",
        description="Worker rejects an assigned pending booking request, returning it to assignment pool.",
        request=WorkerRejectSerializer,
        responses={
            200: OpenApiResponse(description="Booking rejected successfully"),
            400: OpenApiResponse(description="Booking cannot be rejected"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Worker Operations"],
    )
    def post(self, request, booking_number):
        booking = BookingSelector.worker_detail(booking_number, request.user)
        if not booking:
            return Response(
                {"status": "error", "message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if booking.status != BookingStatus.PENDING:
            return Response(
                {"status": "error", "message": "Only pending bookings can be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = WorkerRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            BookingStatusHistory.objects.create(
                booking=booking,
                status=booking.status,
                changed_by=request.user,
                source="worker",
                note=serializer.validated_data.get("reason") or "Worker rejected booking via API."
            )
            booking.worker = None
            booking.save(update_fields=["worker"])
            NotificationService.trigger_worker_rejected(booking, request.user)

            return Response(
                {"status": "success", "message": "Booking rejected successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkerUpdateStatusAPIView(APIView):
    permission_classes = [IsVerifiedWorker]

    @extend_schema(
        operation_id="worker_update_booking_status",
        summary="Update Booking Execution Status",
        description="Transitions status of a booking assigned to the worker (e.g. on_the_way, arrived, started, in_progress, completed).",
        request=WorkerStatusUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Status updated successfully"),
            400: OpenApiResponse(description="Invalid status transition"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Worker Operations"],
    )
    def post(self, request, booking_number):
        booking = BookingSelector.worker_detail(booking_number, request.user)
        if not booking:
            return Response(
                {"status": "error", "message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = WorkerStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        # If transitioning to STARTED / IN_PROGRESS from ARRIVED, enforce OTP verification
        from bookings.services import BookingOTPService
        if new_status in [BookingStatus.STARTED, BookingStatus.IN_PROGRESS] and booking.status == BookingStatus.ARRIVED:
            otp_status = BookingOTPService.get_otp_status(booking)
            if otp_status["is_generated"] and not otp_status["is_verified"]:
                return Response(
                    {"status": "error", "message": "Customer OTP verification is required before starting the job."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            BookingService.change_status(
                booking=booking,
                status=new_status,
                changed_by=request.user,
                source="worker",
                note=serializer.validated_data.get("note", "")
            )

            # Auto-generate OTP when worker arrives so customer receives it immediately
            if new_status == BookingStatus.ARRIVED:
                try:
                    BookingOTPService.generate_otp(booking)
                except Exception:
                    pass

            return Response(
                {"status": "success", "message": f"Booking status updated to {new_status}."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkerTrustScoreAPIView(APIView):
    permission_classes = [IsVerifiedWorker]

    @extend_schema(
        operation_id="get_my_trust_score",
        summary="Retrieve My Trust Score",
        description="Returns the deterministic Trust Score, badge tier, and breakdown signals for the authenticated worker.",
        responses={200: TrustScoreResponseSerializer},
        tags=["Worker Operations"],
    )
    def get(self, request):
        profile = getattr(request.user, "professional_profile", None)
        if not profile:
            return Response(
                {"success": False, "message": "Professional profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        breakdown = TrustScoreService.calculate_score_for_profile(profile)
        return Response(
            {"success": True, "data": breakdown},
            status=status.HTTP_200_OK
        )
