from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework import serializers


class ProfessionalVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["approved", "rejected", "under_review", "suspended"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class BookingAssignSerializer(serializers.Serializer):
    worker_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True)


class AdminSchemas:
    dashboard = extend_schema(
        tags=["Admin Control"],
        summary="Admin Dashboard Real Statistics",
        description="Returns complete operations center metrics for LocalHub admin.",
        responses={
            200: OpenApiResponse(description="Summary metrics dictionary."),
        },
        examples=[
            OpenApiExample(
                "Admin Stats Success Response",
                value={
                    "total_users": 150,
                    "total_professionals": 25,
                    "pending_professional_approvals": 4,
                    "total_categories": 12,
                    "total_services": 45,
                    "pending_bookings": 8,
                    "today_bookings": 3,
                    "total_revenue": 12500.00
                },
                response_only=True,
            )
        ]
    )

    verify_professional = extend_schema(
        tags=["Admin Control"],
        summary="Verify Professional Profile",
        description="Approve or reject a professional profile submission.",
        request=ProfessionalVerifySerializer,
        responses={
            200: OpenApiResponse(description="Verification status updated successfully."),
            400: OpenApiResponse(description="Invalid verification status."),
            404: OpenApiResponse(description="Professional profile not found."),
        }
    )

    assign_booking = extend_schema(
        tags=["Admin Control"],
        summary="Assign Worker or Override Booking Status",
        description="Manually assign a worker or override status for a booking.",
        request=BookingAssignSerializer,
        responses={
            200: OpenApiResponse(description="Worker assigned / status updated successfully."),
            400: OpenApiResponse(description="Invalid request parameter."),
            404: OpenApiResponse(description="Booking or worker not found."),
        }
    )
