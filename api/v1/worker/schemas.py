from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from .serializers import WorkerBookingSerializer, WorkerStatusUpdateSerializer, WorkerRejectSerializer


class WorkerSchemas:
    list_bookings = extend_schema(
        tags=["Worker Workspace"],
        summary="List Worker Bookings",
        description="Returns list of bookings assigned to or pending for the logged-in professional worker.",
        parameters=[
            OpenApiParameter("section", str, description="Filter by workspace section: pending, assigned, or history"),
            OpenApiParameter("status", str, description="Filter by specific booking status string"),
        ],
        responses={
            200: WorkerBookingSerializer(many=True),
        }
    )

    accept_booking = extend_schema(
        tags=["Worker Workspace"],
        summary="Accept Assigned Booking",
        description="Worker accepts an assigned pending booking request.",
        responses={
            200: OpenApiResponse(description="Booking accepted successfully."),
            400: OpenApiResponse(description="Booking cannot be accepted."),
            404: OpenApiResponse(description="Booking not found."),
        },
        examples=[
            OpenApiExample(
                "Accept Success Response",
                value={"status": "success", "message": "Booking accepted successfully."},
                response_only=True,
            )
        ]
    )

    reject_booking = extend_schema(
        tags=["Worker Workspace"],
        summary="Reject Assigned Booking",
        description="Worker rejects an assigned pending booking request, returning it to the pending assignment pool.",
        request=WorkerRejectSerializer,
        responses={
            200: OpenApiResponse(description="Booking rejected successfully."),
            400: OpenApiResponse(description="Booking cannot be rejected."),
            404: OpenApiResponse(description="Booking not found."),
        },
        examples=[
            OpenApiExample(
                "Reject Success Response",
                value={"status": "success", "message": "Booking rejected successfully."},
                response_only=True,
            )
        ]
    )

    update_status = extend_schema(
        tags=["Worker Workspace"],
        summary="Update Booking Status",
        description="Transitions status of a booking assigned to the worker (e.g. ON_THE_WAY, ARRIVED, STARTED, IN_PROGRESS, COMPLETED).",
        request=WorkerStatusUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Status updated successfully."),
            400: OpenApiResponse(description="Invalid status transition."),
            404: OpenApiResponse(description="Booking not found."),
        },
        examples=[
            OpenApiExample(
                "Status Update Request Example",
                value={"status": "on_the_way", "note": "On my way to the customer location."},
                request_only=True,
            ),
            OpenApiExample(
                "Status Update Success Response",
                value={"status": "success", "message": "Booking status updated to on_the_way."},
                response_only=True,
            )
        ]
    )
