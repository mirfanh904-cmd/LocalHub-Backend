from rest_framework import serializers
from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    booking_number = serializers.ReadOnlyField(source="booking.booking_number")

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "booking",
            "booking_number",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "notification_type", "title", "message", "booking", "created_at"]


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
