from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .serializers import NotificationSerializer, UnreadCountSerializer


class NotificationSchemas:
    list = extend_schema(
        tags=["Notifications"],
        summary="List Notifications",
        description="Returns all notifications for the authenticated user, ordered by creation date descending.",
        responses={
            200: NotificationSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "Success Notification List",
                value=[
                    {
                        "id": 1,
                        "notification_type": "BOOKING",
                        "title": "Booking Submitted",
                        "message": "Your booking LH-2026-000001 has been submitted.",
                        "booking": 10,
                        "booking_number": "LH-2026-000001",
                        "is_read": False,
                        "created_at": "2026-07-22T10:00:00Z"
                    }
                ],
                response_only=True,
            )
        ]
    )

    unread_count = extend_schema(
        tags=["Notifications"],
        summary="Get Unread Notification Count",
        description="Returns the total number of unread notifications for the authenticated user.",
        responses={
            200: UnreadCountSerializer,
        },
        examples=[
            OpenApiExample(
                "Unread Count Success",
                value={"unread_count": 3},
                response_only=True,
            )
        ]
    )

    mark_read = extend_schema(
        tags=["Notifications"],
        summary="Mark Single Notification as Read",
        description="Marks a specific notification as read by ID.",
        responses={
            200: OpenApiResponse(description="Notification marked as read successfully."),
            404: OpenApiResponse(description="Notification not found."),
        },
        examples=[
            OpenApiExample(
                "Mark Read Success",
                value={"status": "success", "message": "Notification marked as read."},
                response_only=True,
            )
        ]
    )

    mark_all_read = extend_schema(
        tags=["Notifications"],
        summary="Mark All Notifications as Read",
        description="Marks all unread notifications for the authenticated user as read.",
        responses={
            200: OpenApiResponse(description="All notifications marked as read."),
        },
        examples=[
            OpenApiExample(
                "Mark All Read Success",
                value={"status": "success", "message": "All notifications marked as read."},
                response_only=True,
            )
        ]
    )
