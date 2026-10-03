from django.contrib import admin
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


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "current_balance", "pending_balance", "currency", "is_frozen", "updated_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("is_frozen", "currency")
    readonly_fields = ("created_at", "updated_at")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "transaction_type", "amount", "balance_after", "reference_id", "created_at")
    search_fields = ("wallet__user__email", "reference_id", "description")
    list_filter = ("transaction_type", "created_at")
    readonly_fields = ("wallet", "transaction_type", "amount", "balance_after", "reference_id", "description", "created_at")


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "usage_limit", "used_count", "valid_until", "is_active")
    search_fields = ("code", "description")
    list_filter = ("discount_type", "is_active", "valid_until")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_reference", "customer", "payment_method", "total_amount", "status", "paid_at")
    search_fields = ("payment_reference", "idempotency_key", "customer__email", "gateway_transaction_id")
    list_filter = ("status", "payment_method", "created_at")
    readonly_fields = ("payment_reference", "idempotency_key", "created_at", "updated_at")


@admin.register(EscrowHold)
class EscrowHoldAdmin(admin.ModelAdmin):
    list_display = ("payment", "professional", "held_amount", "status", "released_at")
    search_fields = ("payment__payment_reference", "professional__email", "release_reference")
    list_filter = ("status", "created_at")
    readonly_fields = ("payment", "held_amount", "created_at", "updated_at")


@admin.register(CommissionRecord)
class CommissionRecordAdmin(admin.ModelAdmin):
    list_display = ("payment", "professional", "gross_amount", "commission_amount", "net_earning", "is_settled")
    search_fields = ("payment__payment_reference", "professional__email")
    list_filter = ("is_settled", "created_at")


@admin.register(ProfessionalPayout)
class ProfessionalPayoutAdmin(admin.ModelAdmin):
    list_display = ("payout_reference", "professional", "amount", "payout_method", "status", "processed_at")
    search_fields = ("payout_reference", "professional__email")
    list_filter = ("status", "payout_method", "created_at")


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ("refund_reference", "payment", "customer", "amount", "status", "reviewed_at")
    search_fields = ("refund_reference", "payment__payment_reference", "customer__email")
    list_filter = ("status", "refund_method", "created_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "payment", "customer", "total_amount", "status", "issued_at")
    search_fields = ("invoice_number", "payment__payment_reference", "customer__email", "recipient_name")
    list_filter = ("status", "issued_at")
    readonly_fields = ("invoice_number", "payment", "customer", "issued_at", "created_at", "updated_at")
