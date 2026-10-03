from rest_framework import serializers
from bookings.models import (
    Booking,
    BookingStatusHistory,
    BookingOTP,
    BookingRescheduleRequest,
    RescheduleStatus,
)
from bookings.services import BookingService, BookingOTPService
from accounts.models import Address, User, ProfessionalProfile
from services.models import Service, ServicePackage
from drf_spectacular.utils import extend_schema_field


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True, default="System")

    class Meta:
        model = BookingStatusHistory
        fields = [
            "id",
            "status",
            "changed_by_name",
            "source",
            "note",
            "created_at",
        ]


class BookingOTPVerifySerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True, help_text="6-digit verification OTP")


class BookingOTPStatusSerializer(serializers.Serializer):
    is_generated = serializers.BooleanField()
    is_verified = serializers.BooleanField()
    verified_at = serializers.DateTimeField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    is_expired = serializers.BooleanField()
    is_locked = serializers.BooleanField()
    locked_until = serializers.DateTimeField(allow_null=True)
    attempts = serializers.IntegerField()
    max_attempts = serializers.IntegerField()


class BookingRescheduleRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.full_name", read_only=True)
    responded_by_name = serializers.CharField(source="responded_by.full_name", read_only=True, default=None)

    class Meta:
        model = BookingRescheduleRequest
        fields = [
            "id",
            "requested_by",
            "requested_by_name",
            "original_date",
            "original_start_time",
            "original_end_time",
            "requested_date",
            "requested_start_time",
            "requested_end_time",
            "reason",
            "status",
            "responded_by",
            "responded_by_name",
            "response_note",
            "responded_at",
            "created_at",
        ]


class BookingRescheduleCreateSerializer(serializers.Serializer):
    requested_date = serializers.DateField(required=True)
    requested_start_time = serializers.TimeField(required=True)
    requested_end_time = serializers.TimeField(required=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class BookingRescheduleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject"], required=True)
    response_note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class BookingCreateSerializer(serializers.ModelSerializer):
    booking_number = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True, default=None)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True, default=None)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    worker = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    # Allow flexible input names and auto-calculation
    booking_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = Booking
        fields = (
            "id",
            "booking_number",
            "service",
            "service_name",
            "package",
            "package_name",
            "worker",
            "worker_name",
            "address",
            "booking_date",
            "start_time",
            "end_time",
            "subtotal",
            "discount",
            "platform_fee",
            "tax",
            "total_amount",
            "status",
            "status_display",
            "customer_note",
            "requirements",
            "created_at",
        )
        read_only_fields = ("id", "booking_number", "total_amount", "status", "created_at")

    def to_internal_value(self, data):
        # Support aliases from frontend payloads
        data_copy = data.copy() if hasattr(data, "copy") else dict(data)
        
        if "scheduled_date" in data_copy and "booking_date" not in data_copy:
            data_copy["booking_date"] = data_copy["scheduled_date"]
            
        if "scheduled_time" in data_copy and "start_time" not in data_copy:
            data_copy["start_time"] = data_copy["scheduled_time"]
            
        if "customer_notes" in data_copy and "customer_note" not in data_copy:
            data_copy["customer_note"] = data_copy["customer_notes"]
            
        # Support professional_id or worker_id
        if "worker" not in data_copy:
            raw_worker = data_copy.get("worker_id") or data_copy.get("professional_id") or data_copy.get("professional")
            if raw_worker:
                # If a ProfessionalProfile ID was given, resolve its User ID
                if isinstance(raw_worker, int) or (isinstance(raw_worker, str) and raw_worker.isdigit()):
                    p_id = int(raw_worker)
                    profile_user_id = ProfessionalProfile.objects.filter(id=p_id).values_list("user_id", flat=True).first()
                    if profile_user_id:
                        data_copy["worker"] = profile_user_id
                    else:
                        data_copy["worker"] = p_id
                else:
                    data_copy["worker"] = raw_worker
            
        return super().to_internal_value(data_copy)

    def validate(self, attrs):
        service = attrs.get("service")
        package = attrs.get("package")
        
        # Ensure booking_date is present
        if "booking_date" not in attrs:
            raise serializers.ValidationError({"booking_date": "Booking date is required."})
            
        # Ensure start_time is present
        if "start_time" not in attrs:
            raise serializers.ValidationError({"start_time": "Start time is required."})
            
        # Auto calculate subtotal if not provided
        if "subtotal" not in attrs or attrs["subtotal"] is None:
            if package and getattr(package, "price", None) is not None:
                attrs["subtotal"] = package.price
            elif service and getattr(service, "base_price", None) is not None:
                attrs["subtotal"] = service.base_price
            else:
                attrs["subtotal"] = 0
                
        # Auto calculate end_time if not provided
        if "end_time" not in attrs or attrs["end_time"] is None:
            start_t = attrs["start_time"]
            from datetime import datetime, date, timedelta
            start_dt = datetime.combine(date.today(), start_t)
            
            # Use package or service duration if available, else 1 hour
            duration = timedelta(hours=1)
            if package and getattr(package, "duration_minutes", None):
                duration = timedelta(minutes=package.duration_minutes)
            elif service and getattr(service, "estimated_duration", None):
                from bookings.services import parse_duration_to_timedelta
                duration = parse_duration_to_timedelta(service.estimated_duration)
                
            end_dt = start_dt + duration
            attrs["end_time"] = end_dt.time()
            
        return attrs

    def create(self, validated_data):
        validated_data["customer"] = self.context["request"].user
        
        try:
            return BookingService.create(validated_data)
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)})
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)})


class BookingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = (
            "booking_date",
            "start_time",
            "end_time",
            "customer_note",
        )

    def update(self, instance, validated_data):
        return BookingService.update(instance, validated_data)


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="Cancelled by customer")


class BookingListSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_cover_image = serializers.ImageField(source="service.cover_image", read_only=True)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "booking_number",
            "service_name",
            "service_cover_image",
            "worker_name",
            "booking_date",
            "start_time",
            "end_time",
            "status",
            "status_display",
            "payment_status",
            "total_amount",
            "is_reviewed",
            "created_at",
        )


class BookingDetailSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True, default=None)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True, default=None)
    worker_phone = serializers.CharField(source="worker.phone", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    reschedule_requests = BookingRescheduleRequestSerializer(many=True, read_only=True)
    otp_status = serializers.SerializerMethodField()
    active_reschedule_request = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "service",
            "service_name",
            "package",
            "package_name",
            "package_price",
            "customer",
            "customer_name",
            "customer_phone",
            "worker",
            "worker_name",
            "worker_phone",
            "address",
            "booking_date",
            "start_time",
            "end_time",
            "estimated_duration",
            "status",
            "status_display",
            "payment_status",
            "subtotal",
            "discount",
            "platform_fee",
            "tax",
            "total_amount",
            "customer_note",
            "worker_note",
            "cancelled_reason",
            "cancelled_at",
            "completed_at",
            "is_reviewed",
            "requirements",
            "status_history",
            "reschedule_requests",
            "active_reschedule_request",
            "otp_status",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(BookingOTPStatusSerializer)
    def get_otp_status(self, obj):
        return BookingOTPService.get_otp_status(obj)

    @extend_schema_field(BookingRescheduleRequestSerializer)
    def get_active_reschedule_request(self, obj):
        pending_req = obj.reschedule_requests.filter(status=RescheduleStatus.PENDING).first()
        if pending_req:
            return BookingRescheduleRequestSerializer(pending_req).data
        return None