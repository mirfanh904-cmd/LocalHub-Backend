from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from payments.models import (
    EscrowHold,
    EscrowStatus,
    Payment,
    TransactionType,
)
from .commission_service import CommissionService
from .wallet_service import WalletService
from notifications.models import Notification, NotificationType


class EscrowService:
    @staticmethod
    def create_escrow(payment: Payment, professional=None) -> EscrowHold:
        escrow = EscrowHold.objects.create(
            payment=payment,
            booking=payment.booking,
            task=payment.task,
            professional=professional,
            held_amount=payment.total_amount,
            status=EscrowStatus.HELD,
        )
        if professional:
            WalletService.add_pending_balance(professional, payment.total_amount)
        return escrow

    @classmethod
    def release_booking_escrow(cls, booking) -> bool:
        """
        Releases escrow funds upon booking completion or OTP verification.
        Deducts commission and credits net earnings to the assigned professional.
        """
        with transaction.atomic():
            escrow = EscrowHold.objects.select_for_update().filter(
                booking=booking,
                status=EscrowStatus.HELD,
            ).first()

            if not escrow:
                return False

            professional = booking.worker
            if not professional:
                return False

            # Calculate and record platform commission
            comm_record = CommissionService.create_commission_record(
                payment=escrow.payment,
                professional=professional,
                booking=booking,
            )

            # Credit professional wallet with net earning
            WalletService.remove_pending_balance(professional, escrow.held_amount)
            WalletService.credit_wallet(
                user=professional,
                amount=comm_record.net_earning,
                transaction_type=TransactionType.EARNING_CREDIT,
                reference_id=escrow.payment.payment_reference,
                description=f"Job Earnings (Booking #{booking.booking_number}) - Net after 10% platform fee",
            )

            comm_record.is_settled = True
            comm_record.settled_at = timezone.now()
            comm_record.save(update_fields=["is_settled", "settled_at", "updated_at"])

            escrow.professional = professional
            escrow.status = EscrowStatus.RELEASED
            escrow.released_at = timezone.now()
            escrow.release_reference = f"REL-{booking.booking_number}"
            escrow.save(update_fields=["professional", "status", "released_at", "release_reference", "updated_at"])

            # Send Notification to Professional
            Notification.objects.create(
                user=professional,
                notification_type=NotificationType.PAYMENT,
                title="Payment Released",
                message=f"₹{comm_record.net_earning} has been credited to your wallet for Booking #{booking.booking_number}.",
                booking=booking,
            )

            return True

    @classmethod
    def release_task_escrow(cls, task) -> bool:
        """
        Releases escrow funds upon task completion.
        """
        with transaction.atomic():
            escrow = EscrowHold.objects.select_for_update().filter(
                task=task,
                status=EscrowStatus.HELD,
            ).first()

            if not escrow:
                return False

            professional = task.assigned_professional
            if not professional:
                return False

            comm_record = CommissionService.create_commission_record(
                payment=escrow.payment,
                professional=professional,
                task=task,
            )

            WalletService.remove_pending_balance(professional, escrow.held_amount)
            WalletService.credit_wallet(
                user=professional,
                amount=comm_record.net_earning,
                transaction_type=TransactionType.EARNING_CREDIT,
                reference_id=escrow.payment.payment_reference,
                description=f"Task Earnings (Task #{task.task_number}) - Net after 10% platform fee",
            )

            comm_record.is_settled = True
            comm_record.settled_at = timezone.now()
            comm_record.save(update_fields=["is_settled", "settled_at", "updated_at"])

            escrow.professional = professional
            escrow.status = EscrowStatus.RELEASED
            escrow.released_at = timezone.now()
            escrow.release_reference = f"REL-{task.task_number}"
            escrow.save(update_fields=["professional", "status", "released_at", "release_reference", "updated_at"])

            Notification.objects.create(
                user=professional,
                notification_type=NotificationType.PAYMENT,
                title="Task Payment Released",
                message=f"₹{comm_record.net_earning} has been credited to your wallet for Task #{task.task_number}.",
            )

            return True
