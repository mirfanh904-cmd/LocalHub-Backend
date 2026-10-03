from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from payments.models import (
    ProfessionalPayout,
    PayoutStatus,
    PayoutMethod,
    TransactionType,
)
from .wallet_service import WalletService
from notifications.models import Notification, NotificationType


class PayoutService:
    MINIMUM_PAYOUT_AMOUNT = Decimal("500.00")

    @classmethod
    def request_payout(
        cls,
        professional,
        amount: Decimal,
        payout_method: str = PayoutMethod.UPI,
        account_details: dict = None,
    ) -> ProfessionalPayout:
        if amount < cls.MINIMUM_PAYOUT_AMOUNT:
            raise ValidationError(f"Minimum payout withdrawal amount is ₹{cls.MINIMUM_PAYOUT_AMOUNT}.")

        wallet = WalletService.get_or_create_wallet(professional)
        if wallet.current_balance < amount:
            raise ValidationError(
                f"Insufficient available wallet balance. Available: ₹{wallet.current_balance}, Requested: ₹{amount}."
            )

        year = timezone.now().year
        count = ProfessionalPayout.objects.filter(created_at__year=year).count() + 1
        payout_ref = f"PO-{year}-{count:04d}"

        with transaction.atomic():
            # Debit available wallet immediately and place in pending payout
            WalletService.debit_wallet(
                user=professional,
                amount=amount,
                transaction_type=TransactionType.PAYOUT_DEBIT,
                reference_id=payout_ref,
                description=f"Withdrawal Request {payout_ref} ({payout_method})",
            )
            WalletService.add_pending_balance(professional, amount)

            payout = ProfessionalPayout.objects.create(
                payout_reference=payout_ref,
                professional=professional,
                amount=amount,
                payout_method=payout_method,
                account_details=account_details or {},
                status=PayoutStatus.REQUESTED,
            )

            Notification.objects.create(
                user=professional,
                notification_type=NotificationType.PAYMENT,
                title="Payout Request Submitted",
                message=f"Your withdrawal request of ₹{amount} ({payout_ref}) has been submitted for admin processing.",
            )

            return payout

    @classmethod
    def process_payout_action(
        cls,
        payout: ProfessionalPayout,
        action: str,  # 'COMPLETE' | 'FAIL'
        admin_user,
        admin_notes: str = "",
        failure_reason: str = "",
    ) -> ProfessionalPayout:
        if payout.status not in [PayoutStatus.REQUESTED, PayoutStatus.PROCESSING]:
            raise ValidationError(f"Cannot process payout with status {payout.status}.")

        with transaction.atomic():
            professional = payout.professional

            if action == "COMPLETE":
                WalletService.remove_pending_balance(professional, payout.amount)
                payout.status = PayoutStatus.COMPLETED
                payout.processed_at = timezone.now()
                payout.processed_by = admin_user
                payout.admin_notes = admin_notes
                payout.save(update_fields=["status", "processed_at", "processed_by", "admin_notes", "updated_at"])

                Notification.objects.create(
                    user=professional,
                    notification_type=NotificationType.PAYMENT,
                    title="Payout Settled",
                    message=f"Your payout of ₹{payout.amount} ({payout.payout_reference}) has been processed and transferred.",
                )
                return payout

            elif action == "FAIL":
                # Re-credit wallet balance and remove from pending
                WalletService.remove_pending_balance(professional, payout.amount)
                WalletService.credit_wallet(
                    user=professional,
                    amount=payout.amount,
                    transaction_type=TransactionType.ADJUSTMENT,
                    reference_id=payout.payout_reference,
                    description=f"Reversal for Failed Payout {payout.payout_reference}: {failure_reason or 'Bank processing error'}",
                )

                payout.status = PayoutStatus.FAILED
                payout.processed_at = timezone.now()
                payout.processed_by = admin_user
                payout.admin_notes = admin_notes
                payout.failure_reason = failure_reason
                payout.save(update_fields=["status", "processed_at", "processed_by", "admin_notes", "failure_reason", "updated_at"])

                Notification.objects.create(
                    user=professional,
                    notification_type=NotificationType.PAYMENT,
                    title="Payout Failed & Re-credited",
                    message=f"Payout {payout.payout_reference} could not be completed. ₹{payout.amount} has been refunded to your wallet balance.",
                )
                return payout
            else:
                raise ValidationError("Invalid action. Expected 'COMPLETE' or 'FAIL'.")
