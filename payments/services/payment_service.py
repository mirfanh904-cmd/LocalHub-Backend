from decimal import Decimal
from typing import Any, Dict, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from payments.models import (
    Payment,
    PaymentMethod,
    PaymentStatus,
    PromoCode,
    TransactionType,
)
from payments.gateway import MockPaymentGateway
from .wallet_service import WalletService
from .escrow_service import EscrowService
from .invoice_service import InvoiceService
from notifications.models import Notification, NotificationType
from bookings.models import Booking, PaymentStatus as BookingPaymentStatus
from tasks.models import Task


class PaymentService:
    @classmethod
    def process_checkout(
        cls,
        customer,
        target_type: str,  # 'booking' | 'task'
        target_id: str,
        payment_method: str,  # 'CASH' | 'ONLINE' | 'WALLET'
        idempotency_key: str,
        promo_code_str: Optional[str] = None,
        gateway_txn_id: Optional[str] = None,
    ) -> Payment:
        # 1. Idempotency Check
        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing_payment:
            return existing_payment

        # 2. Fetch target object
        booking = None
        task = None
        subtotal = Decimal("0.00")
        assigned_pro = None

        if target_type == "booking":
            booking = Booking.objects.select_related("service", "worker", "address").get(id=target_id, customer=customer)
            subtotal = booking.total_amount
            assigned_pro = booking.worker
        elif target_type == "task":
            task = Task.objects.select_related("assigned_professional", "accepted_application").get(id=target_id, customer=customer)
            if task.accepted_application:
                subtotal = task.accepted_application.proposed_price
            else:
                subtotal = task.budget
            assigned_pro = task.assigned_professional
        else:
            raise ValidationError("Invalid target_type. Expected 'booking' or 'task'.")

        # 3. Apply Promo Code
        promo_code = None
        discount_amount = Decimal("0.00")
        if promo_code_str:
            promo = PromoCode.objects.filter(code__iexact=promo_code_str.strip()).first()
            if promo:
                valid, msg = promo.is_valid(subtotal)
                if not valid:
                    raise ValidationError(f"Invalid promo code: {msg}")
                discount_amount = promo.calculate_discount(subtotal)
                promo_code = promo
            else:
                raise ValidationError("Promo code not found.")

        platform_fee = Decimal("0.00")
        total_amount = max(Decimal("0.00"), subtotal - discount_amount + platform_fee)

        year = timezone.now().year
        count = Payment.objects.filter(created_at__year=year).count() + 1
        payment_reference = f"PAY-{year}-{count:05d}"

        # 4. Atomic Execution based on Payment Method
        with transaction.atomic():
            payment = Payment.objects.create(
                payment_reference=payment_reference,
                idempotency_key=idempotency_key,
                customer=customer,
                booking=booking,
                task=task,
                payment_method=payment_method,
                status=PaymentStatus.PENDING,
                subtotal=subtotal,
                discount_amount=discount_amount,
                promo_code=promo_code,
                platform_fee=platform_fee,
                total_amount=total_amount,
                gateway_transaction_id=gateway_txn_id or "",
            )

            if promo_code:
                promo_code.used_count += 1
                promo_code.save(update_fields=["used_count", "updated_at"])

            if payment_method == PaymentMethod.WALLET:
                # Debit customer wallet
                WalletService.debit_wallet(
                    user=customer,
                    amount=total_amount,
                    transaction_type=TransactionType.WALLET_DEBIT,
                    reference_id=payment_reference,
                    description=f"Payment for {target_type.capitalize()} #{booking.booking_number if booking else task.task_number}",
                )
                payment.status = PaymentStatus.COMPLETED
                payment.paid_at = timezone.now()
                payment.save(update_fields=["status", "paid_at", "updated_at"])

            elif payment_method == PaymentMethod.ONLINE:
                # Mock gateway verification
                gateway = MockPaymentGateway()
                txn_id = gateway_txn_id or f"mock_tx_{payment_reference}"
                if gateway.verify_payment(txn_id, payment_reference, total_amount):
                    payment.status = PaymentStatus.COMPLETED
                    payment.paid_at = timezone.now()
                    payment.gateway_transaction_id = txn_id
                    payment.save(update_fields=["status", "paid_at", "gateway_transaction_id", "updated_at"])
                else:
                    payment.status = PaymentStatus.FAILED
                    payment.save(update_fields=["status", "updated_at"])
                    raise ValidationError("Online payment verification failed.")

            elif payment_method == PaymentMethod.CASH:
                # Payment stays PENDING until job completion
                payment.status = PaymentStatus.PENDING
                payment.save(update_fields=["status", "updated_at"])

            # 5. Escrow Hold creation if online or wallet
            if payment.status == PaymentStatus.COMPLETED:
                EscrowService.create_escrow(payment, professional=assigned_pro)

            # 6. Update Booking status if booking
            if booking:
                if payment.status == PaymentStatus.COMPLETED:
                    booking.payment_status = BookingPaymentStatus.PAID
                booking.save(update_fields=["payment_status", "updated_at"])

            # 7. Generate Invoice
            InvoiceService.generate_invoice(payment)

            # 8. Notification
            Notification.objects.create(
                user=customer,
                notification_type=NotificationType.PAYMENT,
                title="Payment Confirmation",
                message=f"Payment of ₹{total_amount} recorded for {target_type.capitalize()} (Ref: {payment_reference}).",
                booking=booking,
            )

            return payment
