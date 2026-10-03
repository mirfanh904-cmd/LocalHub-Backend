from rest_framework import serializers
from bookings.models import Review, ReviewReply, ReviewReport, ReportReason


class ReviewReplySerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.full_name", read_only=True)

    class Meta:
        model = ReviewReply
        fields = [
            "id",
            "professional_name",
            "comment",
            "created_at",
            "updated_at",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    booking_number = serializers.CharField(source="booking.booking_number", read_only=True)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True, default=None)
    reply = ReviewReplySerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "booking_number",
            "customer_name",
            "worker_name",
            "service_name",
            "rating",
            "comment",
            "reply",
            "created_at",
        ]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewReplyCreateSerializer(serializers.Serializer):
    comment = serializers.CharField(max_length=2000, help_text="Official response from professional")


class ReviewReportCreateSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=ReportReason.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
