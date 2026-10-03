from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiResponse

from api.permissions import IsCustomer, IsComplaintOwnerOrAdmin
from bookings.models import Complaint, Booking
from bookings.services import ComplaintService
from .serializers import (
    ComplaintCreateSerializer,
    ComplaintListSerializer,
    ComplaintDetailSerializer,
)


class ComplaintListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_my_complaints",
        summary="List My Complaints",
        description="Returns all Trust & Safety complaints filed by the authenticated customer.",
        responses={200: ComplaintListSerializer(many=True)},
        tags=["Complaints"],
    )
    def get(self, request):
        complaints = Complaint.objects.filter(customer=request.user).order_by("-created_at")
        serializer = ComplaintListSerializer(complaints, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="create_complaint",
        summary="Create Complaint",
        description="File a Trust & Safety complaint or dispute against a service, booking, or professional.",
        request=ComplaintCreateSerializer,
        responses={
            201: ComplaintDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["Complaints"],
    )
    def post(self, request):
        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = None
        booking_number = serializer.validated_data.get("booking_number")
        if booking_number:
            booking = get_object_or_404(Booking, booking_number=booking_number)

        try:
            complaint = ComplaintService.create_complaint(
                customer=request.user,
                category=serializer.validated_data["category"],
                subject=serializer.validated_data["subject"],
                description=serializer.validated_data["description"],
                booking=booking,
                priority=serializer.validated_data.get("priority", "medium"),
            )
            return Response(
                {
                    "success": True,
                    "message": "Complaint filed successfully. Our Trust & Safety team will review it shortly.",
                    "data": ComplaintDetailSerializer(complaint).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ComplaintDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsComplaintOwnerOrAdmin]

    @extend_schema(
        operation_id="retrieve_complaint_detail",
        summary="Retrieve Complaint Detail",
        description="Retrieves status, investigation details, and resolution of a filed complaint.",
        responses={
            200: ComplaintDetailSerializer,
            403: OpenApiResponse(description="Access forbidden (IDOR protection)"),
            404: OpenApiResponse(description="Complaint not found"),
        },
        tags=["Complaints"],
    )
    def get(self, request, complaint_number):
        complaint = get_object_or_404(Complaint, complaint_number=complaint_number)
        self.check_object_permissions(request, complaint)
        return Response(
            {"success": True, "data": ComplaintDetailSerializer(complaint).data},
            status=status.HTTP_200_OK,
        )
