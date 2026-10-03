from rest_framework import serializers
from payments.models import (
    Payment,
    RefundRequest,
    ProfessionalPayout,
    CommissionRecord,
    EscrowHold,
    PromoCode,
)


class AdminFinancialOverviewSerializer(serializers.Serializer):
    total_platform_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_commission_earned = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_payments_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_escrow_held = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_payouts_completed = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_refunds_processed = serializers.DecimalField(max_digits=14, decimal_places=2)
    pending_refunds_count = serializers.IntegerField()
    pending_payouts_count = serializers.IntegerField()


class AdminRefundActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")


class AdminPayoutActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["COMPLETE", "FAIL"])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")
    failure_reason = serializers.CharField(required=False, allow_blank=True, default="")


class AdminPromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "min_order_amount",
            "valid_from",
            "valid_until",
            "usage_limit",
            "used_count",
            "is_active",
            "created_at",
        ]
