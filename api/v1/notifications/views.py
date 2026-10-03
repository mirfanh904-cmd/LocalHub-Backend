from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from notifications.selectors import NotificationSelector
from notifications.services import NotificationService
from .serializers import NotificationSerializer, UnreadCountSerializer


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_user_notifications",
        summary="List Notifications",
        description="Returns in-app notifications for the authenticated user.",
        tags=["Notifications"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return NotificationSelector.user_notifications(self.request.user)


class UnreadNotificationCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_unread_notification_count",
        summary="Get Unread Notification Count",
        description="Returns count of unread in-app notifications.",
        responses={200: UnreadCountSerializer},
        tags=["Notifications"],
    )
    def get(self, request):
        count = NotificationSelector.unread_count(request.user)
        return Response({"unread_count": count}, status=status.HTTP_200_OK)


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="mark_notification_read",
        summary="Mark Notification as Read",
        description="Marks a specific notification as read by ID.",
        request=None,
        responses={
            200: OpenApiResponse(description="Notification marked as read"),
            404: OpenApiResponse(description="Notification not found"),
        },
        tags=["Notifications"],
    )
    def post(self, request, pk):
        success = NotificationService.mark_as_read(pk, request.user)
        if success:
            return Response(
                {"success": True, "message": "Notification marked as read."},
                status=status.HTTP_200_OK
            )
        return Response(
            {"success": False, "message": "Notification not found."},
            status=status.HTTP_404_NOT_FOUND
        )


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="mark_all_notifications_read",
        summary="Mark All Notifications as Read",
        description="Marks all unread notifications for the user as read.",
        request=None,
        responses={200: OpenApiResponse(description="All notifications marked as read")},
        tags=["Notifications"],
    )
    def post(self, request):
        NotificationService.mark_all_as_read(request.user)
        return Response(
            {"success": True, "message": "All notifications marked as read."},
            status=status.HTTP_200_OK
        )
