from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from bookings.models import (
    Booking,
    BookingStatus,
    BookingRescheduleRequest,
    RescheduleStatus,
)
from bookings.selectors import BookingSelector
from bookings.services import (
    BookingService,
    BookingOTPService,
    BookingRescheduleService,
)
from .serializers import (
    BookingCreateSerializer,
    BookingUpdateSerializer,
    BookingCancelSerializer,
    BookingListSerializer,
    BookingDetailSerializer,
    BookingOTPVerifySerializer,
    BookingOTPStatusSerializer,
    BookingRescheduleRequestSerializer,
    BookingRescheduleCreateSerializer,
    BookingRescheduleResponseSerializer,
)


class BookingCreateAPIView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="create_booking",
        summary="Create Booking",
        description="Creates a new service booking for the authenticated customer.",
        request=BookingCreateSerializer,
        responses={
            201: BookingDetailSerializer,
            400: OpenApiResponse(description="Validation error (e.g. overlapping time, invalid address)"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Bookings"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BookingListAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookingCreateSerializer
        return BookingListSerializer

    @extend_schema(
        operation_id="list_or_create_bookings",
        summary="List or Create Bookings",
        description="Returns customer bookings on GET, or creates a new booking on POST.",
        responses={200: BookingListSerializer(many=True), 201: BookingCreateSerializer},
        tags=["Bookings"],
    )
    def get_queryset(self):
        return BookingSelector.my_bookings(self.request.user)


class BookingDetailAPIView(generics.RetrieveAPIView):
    serializer_class = BookingDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "booking_number"

    @extend_schema(
        operation_id="retrieve_booking_detail",
        summary="Retrieve Booking Details",
        description="Retrieves complete booking details, live status audit history, OTP status, and reschedule information using the booking number.",
        responses={
            200: BookingDetailSerializer,
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Bookings"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        booking_param = self.kwargs.get("booking_number")
        user = self.request.user
        
        lookup_filter = Q(booking_number=booking_param)
        if str(booking_param).isdigit():
            lookup_filter |= Q(id=int(booking_param))

        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = Booking.objects.filter(lookup_filter).first()
        else:
            booking = Booking.objects.filter(
                lookup_filter & (Q(customer=user) | Q(worker=user))
            ).first()
        if not booking:
            raise Http404("Booking not found or you are not authorized to view it.")
        return booking


class BookingUpdateAPIView(generics.UpdateAPIView):
    serializer_class = BookingUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "booking_number"

    @extend_schema(
        operation_id="update_booking",
        summary="Update Booking",
        description="Modifies scheduled date, time, or customer note on an active pending booking.",
        request=BookingUpdateSerializer,
        responses={
            200: BookingDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["Bookings"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_queryset(self):
        return BookingSelector.my_bookings(self.request.user)


class BookingCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="cancel_booking",
        summary="Cancel Booking",
        description="Cancels an active booking with an auditable cancellation reason.",
        request=BookingCancelSerializer,
        responses={
            200: BookingDetailSerializer,
            400: OpenApiResponse(description="Booking cannot be cancelled in its current state"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Bookings"],
    )
    def post(self, request, booking_number):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = get_object_or_404(Booking, booking_number=booking_number)
        else:
            booking = get_object_or_404(Booking, Q(booking_number=booking_number) & (Q(customer=user) | Q(worker=user)))

        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = "worker" if user == booking.worker else ("customer" if user == booking.customer else "admin")

        try:
            booking = BookingService.cancel(
                booking=booking,
                changed_by=user,
                cancelled_reason=serializer.validated_data.get("reason", "Cancelled by user"),
                source=source,
            )
            return Response(
                {
                    "success": True,
                    "message": "Booking cancelled successfully.",
                    "data": BookingDetailSerializer(booking).data,
                },
                status=status.HTTP_200_OK,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BookingOTPGenerateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="generate_booking_otp",
        summary="Generate Booking Service OTP",
        description="Generates a 6-digit cryptographically secure OTP for job start verification and dispatches notification.",
        request=None,
        responses={
            200: OpenApiResponse(description="OTP generated successfully"),
            400: OpenApiResponse(description="Invalid request or booking state"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Booking Lifecycle & OTP"],
    )
    def post(self, request, booking_number):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = get_object_or_404(Booking, booking_number=booking_number)
        else:
            booking = get_object_or_404(Booking, booking_number=booking_number, customer=user)

        try:
            BookingOTPService.generate_otp(booking)
            return Response(
                {
                    "success": True,
                    "message": "Verification OTP generated successfully.",
                    "data": BookingOTPService.get_otp_status(booking),
                },
                status=status.HTTP_200_OK,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BookingOTPVerifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="verify_booking_otp",
        summary="Verify Booking Service OTP",
        description="Professional worker enters customer 6-digit OTP to verify presence and start the service.",
        request=BookingOTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="OTP verified successfully, work started"),
            400: OpenApiResponse(description="Invalid OTP or maximum attempts reached"),
            403: OpenApiResponse(description="Forbidden - only assigned worker can verify"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Booking Lifecycle & OTP"],
    )
    def post(self, request, booking_number):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = get_object_or_404(Booking, booking_number=booking_number)
        else:
            booking = get_object_or_404(Booking, booking_number=booking_number, worker=user)

        serializer = BookingOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            BookingOTPService.verify_otp(
                booking=booking,
                entered_otp=serializer.validated_data["otp_code"],
                verified_by=user,
            )
            # Reload fresh booking instance
            booking.refresh_from_db()
            return Response(
                {
                    "success": True,
                    "message": "OTP verified successfully. Work has commenced.",
                    "data": BookingDetailSerializer(booking).data,
                },
                status=status.HTTP_200_OK,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BookingOTPStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_booking_otp_status",
        summary="Get Booking OTP Status",
        description="Returns live OTP verification status, lock state, and expiration metadata for the booking.",
        responses={200: BookingOTPStatusSerializer},
        tags=["Booking Lifecycle & OTP"],
    )
    def get(self, request, booking_number):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = get_object_or_404(Booking, booking_number=booking_number)
        else:
            booking = get_object_or_404(
                Booking,
                Q(booking_number=booking_number) & (Q(customer=user) | Q(worker=user)),
            )

        status_data = BookingOTPService.get_otp_status(booking)
        return Response({"success": True, "data": status_data}, status=status.HTTP_200_OK)


class BookingRescheduleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_booking_reschedule_requests",
        summary="List Reschedule Requests",
        description="Returns all reschedule requests for this booking.",
        responses={200: BookingRescheduleRequestSerializer(many=True)},
        tags=["Booking Rescheduling"],
    )
    def get(self, request, booking_number):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = get_object_or_404(Booking, booking_number=booking_number)
        else:
            booking = get_object_or_404(
                Booking,
                Q(booking_number=booking_number) & (Q(customer=user) | Q(worker=user)),
            )

        requests = booking.reschedule_requests.all().order_by("-created_at")
        return Response(
            {"success": True, "data": BookingRescheduleRequestSerializer(requests, many=True).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="create_booking_reschedule_request",
        summary="Request Booking Reschedule",
        description="Initiates an audited reschedule request for a new date/time slot.",
        request=BookingRescheduleCreateSerializer,
        responses={
            201: BookingRescheduleRequestSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Booking not found"),
        },
        tags=["Booking Rescheduling"],
    )
    def post(self, request, booking_number):
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            booking = get_object_or_404(Booking, booking_number=booking_number)
        else:
            booking = get_object_or_404(
                Booking,
                Q(booking_number=booking_number) & (Q(customer=user) | Q(worker=user)),
            )

        serializer = BookingRescheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req_obj = BookingRescheduleService.create_request(
                booking=booking,
                requested_by=user,
                requested_date=serializer.validated_data["requested_date"],
                requested_start_time=serializer.validated_data["requested_start_time"],
                requested_end_time=serializer.validated_data["requested_end_time"],
                reason=serializer.validated_data.get("reason", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Reschedule request created successfully.",
                    "data": BookingRescheduleRequestSerializer(req_obj).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BookingRescheduleRespondAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="respond_booking_reschedule_request",
        summary="Respond to Reschedule Request",
        description="Accepts or rejects an incoming pending reschedule request.",
        request=BookingRescheduleResponseSerializer,
        responses={
            200: BookingRescheduleRequestSerializer,
            400: OpenApiResponse(description="Validation error or invalid request state"),
            404: OpenApiResponse(description="Reschedule request not found"),
        },
        tags=["Booking Rescheduling"],
    )
    def post(self, request, booking_number, request_id):
        user = request.user
        booking = get_object_or_404(
            Booking,
            Q(booking_number=booking_number) & (Q(customer=user) | Q(worker=user) | Q(customer__isnull=False)),
        )
        reschedule_request = get_object_or_404(
            BookingRescheduleRequest,
            id=request_id,
            booking=booking,
        )

        serializer = BookingRescheduleResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req_obj = BookingRescheduleService.respond_request(
                reschedule_request=reschedule_request,
                user=user,
                action=serializer.validated_data["action"],
                response_note=serializer.validated_data.get("response_note", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": f"Reschedule request {req_obj.status} successfully.",
                    "data": BookingRescheduleRequestSerializer(req_obj).data,
                },
                status=status.HTTP_200_OK,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )