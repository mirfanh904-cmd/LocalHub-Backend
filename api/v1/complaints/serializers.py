from rest_framework import serializers
from bookings.models import Complaint, ComplaintCategory, ComplaintPriority


class ComplaintCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=ComplaintCategory.choices)
    subject = serializers.CharField(max_length=200)
    description = serializers.CharField()
    booking_number = serializers.CharField(max_length=30, required=False, allow_blank=True, help_text="Optional booking number related to this complaint")
    priority = serializers.ChoiceField(choices=ComplaintPriority.choices, default=ComplaintPriority.MEDIUM)


class ComplaintListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "category",
            "category_display",
            "subject",
            "status",
            "status_display",
            "priority",
            "created_at",
        ]


class ComplaintDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    booking_number = serializers.CharField(source="booking.booking_number", read_only=True, default=None)
    professional_name = serializers.CharField(source="professional.full_name", read_only=True, default=None)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "category",
            "category_display",
            "subject",
            "description",
            "status",
            "status_display",
            "priority",
            "resolution",
            "booking_number",
            "professional_name",
            "created_at",
            "resolved_at",
        ]
