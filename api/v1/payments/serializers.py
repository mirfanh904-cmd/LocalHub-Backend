from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from payments.models import (
    Wallet,
    WalletTransaction,
    PromoCode,
    Payment,
    EscrowHold,
    CommissionRecord,
    ProfessionalPayout,
    RefundRequest,
    Invoice,
)


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "transaction_type",
            "amount",
            "balance_after",
            "reference_id",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            "id",
            "current_balance",
            "pending_balance",
            "currency",
            "is_frozen",
            "recent_transactions",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(WalletTransactionSerializer(many=True))
    def get_recent_transactions(self, obj):
        txns = obj.transactions.all()[:10]
        return WalletTransactionSerializer(txns, many=True).data


class WalletTopupSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("10.00"))


class PromoCodeValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=30)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))


class PromoCodeResponseSerializer(serializers.ModelSerializer):
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PromoCode
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "discount_amount",
            "final_amount",
            "min_order_amount",
        ]


class CheckoutRequestSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=["booking", "task"])
    target_id = serializers.CharField()
    payment_method = serializers.ChoiceField(choices=["CASH", "ONLINE", "WALLET"])
    idempotency_key = serializers.CharField(max_length=120)
    promo_code = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    gateway_transaction_id = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_reference",
            "idempotency_key",
            "payment_method",
            "status",
            "subtotal",
            "discount_amount",
            "platform_fee",
            "total_amount",
            "paid_at",
            "gateway_transaction_id",
            "created_at",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source="payment.payment_reference", read_only=True)
    payment_method = serializers.CharField(source="payment.payment_method", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "payment_reference",
            "payment_method",
            "recipient_name",
            "recipient_email",
            "recipient_address",
            "service_summary",
            "subtotal",
            "discount",
            "platform_fee",
            "tax",
            "total_amount",
            "status",
            "issued_at",
            "pdf_url",
        ]
        read_only_fields = fields


class RefundRequestCreateSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1.00"))
    reason = serializers.CharField()
    refund_method = serializers.ChoiceField(choices=["WALLET_CREDIT", "ORIGINAL_SOURCE"], default="WALLET_CREDIT")


class RefundRequestSerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source="payment.payment_reference", read_only=True)

    class Meta:
        model = RefundRequest
        fields = [
            "id",
            "refund_reference",
            "payment_id",
            "payment_reference",
            "amount",
            "reason",
            "refund_method",
            "status",
            "admin_notes",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields


class ProfessionalEarningsSerializer(serializers.Serializer):
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_escrow = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_gross_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_commission_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_net_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_withdrawn = serializers.DecimalField(max_digits=12, decimal_places=2)
    earnings_breakdown = serializers.ListField(child=serializers.DictField())


class PayoutRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("500.00"))
    payout_method = serializers.ChoiceField(choices=["UPI", "BANK_TRANSFER"], default="UPI")
    account_details = serializers.DictField()


class ProfessionalPayoutSerializer(serializers.ModelSerializer):
    professional_email = serializers.CharField(source="professional.email", read_only=True)
    professional_name = serializers.CharField(source="professional.full_name", read_only=True)

    class Meta:
        model = ProfessionalPayout
        fields = [
            "id",
            "payout_reference",
            "professional_email",
            "professional_name",
            "amount",
            "payout_method",
            "account_details",
            "status",
            "processed_at",
            "admin_notes",
            "failure_reason",
            "created_at",
        ]
        read_only_fields = fields
