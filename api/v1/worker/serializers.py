from rest_framework import serializers
from bookings.models import Booking, BookingStatus


class WorkerBookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "customer_name",
            "service_name",
            "booking_date",
            "start_time",
            "end_time",
            "status",
            "total_amount",
            "created_at",
        ]
        read_only_fields = fields


class WorkerStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=BookingStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class WorkerRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
