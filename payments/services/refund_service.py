from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from payments.models import (
    Payment,
    PaymentStatus,
    RefundRequest,
    RefundStatus,
    RefundMethod,
    EscrowHold,
    EscrowStatus,
    TransactionType,
    Invoice,
    InvoiceStatus,
)
from .wallet_service import WalletService
from notifications.models import Notification, NotificationType


class RefundService:
    @staticmethod
    def request_refund(
        customer,
        payment_id: str,
        amount: Decimal,
        reason: str,
        refund_method: str = RefundMethod.WALLET_CREDIT,
    ) -> RefundRequest:
        payment = Payment.objects.get(id=payment_id, customer=customer)

        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError("Refunds can only be requested for completed payments.")

        if amount > payment.total_amount:
            raise ValidationError(f"Refund amount (₹{amount}) exceeds total paid (₹{payment.total_amount}).")

        # Check existing refund requests
        existing_refund = RefundRequest.objects.filter(payment=payment, status__in=[RefundStatus.PENDING, RefundStatus.APPROVED, RefundStatus.COMPLETED]).first()
        if existing_refund:
            raise ValidationError(f"A refund request ({existing_refund.refund_reference}) already exists for this payment.")

        year = timezone.now().year
        count = RefundRequest.objects.filter(created_at__year=year).count() + 1
        ref_number = f"REF-{year}-{count:04d}"

        refund = RefundRequest.objects.create(
            refund_reference=ref_number,
            payment=payment,
            customer=customer,
            amount=amount,
            reason=reason,
            refund_method=refund_method,
            status=RefundStatus.PENDING,
        )
        return refund

    @classmethod
    def process_refund_action(
        cls,
        refund_request: RefundRequest,
        action: str,  # 'APPROVE' | 'REJECT'
        admin_user,
        admin_notes: str = "",
    ) -> RefundRequest:
        if refund_request.status != RefundStatus.PENDING:
            raise ValidationError(f"Cannot process refund with status {refund_request.status}.")

        with transaction.atomic():
            if action == "REJECT":
                refund_request.status = RefundStatus.REJECTED
                refund_request.reviewed_by = admin_user
                refund_request.reviewed_at = timezone.now()
                refund_request.admin_notes = admin_notes
                refund_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "admin_notes", "updated_at"])

                Notification.objects.create(
                    user=refund_request.customer,
                    notification_type=NotificationType.PAYMENT,
                    title="Refund Request Rejected",
                    message=f"Your refund request {refund_request.refund_reference} was rejected. Note: {admin_notes}",
                )
                return refund_request

            elif action == "APPROVE":
                payment = refund_request.payment
                customer = refund_request.customer

                # Check if escrow is still held
                escrow = EscrowHold.objects.filter(payment=payment, status=EscrowStatus.HELD).first()
                if escrow:
                    if escrow.professional:
                        WalletService.remove_pending_balance(escrow.professional, escrow.held_amount)
                    escrow.status = EscrowStatus.REFUNDED
                    escrow.save(update_fields=["status", "updated_at"])

                # Credit refund amount to customer wallet
                WalletService.credit_wallet(
                    user=customer,
                    amount=refund_request.amount,
                    transaction_type=TransactionType.REFUND_CREDIT,
                    reference_id=refund_request.refund_reference,
                    description=f"Refund for Payment {payment.payment_reference}",
                )

                # Mark Payment and Invoice status
                payment.status = PaymentStatus.REFUNDED
                payment.save(update_fields=["status", "updated_at"])

                invoice = Invoice.objects.filter(payment=payment).first()
                if invoice:
                    invoice.status = InvoiceStatus.REFUNDED
                    invoice.save(update_fields=["status", "updated_at"])

                refund_request.status = RefundStatus.COMPLETED
                refund_request.reviewed_by = admin_user
                refund_request.reviewed_at = timezone.now()
                refund_request.admin_notes = admin_notes
                refund_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "admin_notes", "updated_at"])

                Notification.objects.create(
                    user=customer,
                    notification_type=NotificationType.PAYMENT,
                    title="Refund Approved & Credited",
                    message=f"Your refund of ₹{refund_request.amount} ({refund_request.refund_reference}) has been credited to your wallet.",
                )

                return refund_request
            else:
                raise ValidationError("Invalid action. Must be 'APPROVE' or 'REJECT'.")
