from decimal import Decimal
from django.utils import timezone
from payments.models import Invoice, InvoiceStatus, Payment


class InvoiceService:
    @staticmethod
    def generate_invoice(payment: Payment) -> Invoice:
        if hasattr(payment, "invoice"):
            return payment.invoice

        year = timezone.now().year
        count = Invoice.objects.filter(created_at__year=year).count() + 1
        invoice_number = f"INV-{year}-{count:05d}"

        # Resolve customer details & summary
        customer = payment.customer
        recipient_name = customer.full_name or customer.email
        recipient_email = customer.email
        recipient_address = ""
        service_summary = "LocalHub Service Booking"

        if payment.booking:
            booking = payment.booking
            svc_name = getattr(booking.service, "name", getattr(booking.service, "title", "Service"))
            service_summary = f"{svc_name} ({booking.booking_number})"
            if booking.address:
                recipient_address = f"{booking.address.house_name}, {booking.address.area}, {booking.address.city} - {booking.address.postal_code}"
        elif payment.task:
            task = payment.task
            service_summary = f"Custom Task: {task.title} ({task.task_number})"
            recipient_address = f"{task.house_name}, {task.area}, {task.city} - {task.postal_code}"

        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            payment=payment,
            customer=customer,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            recipient_address=recipient_address,
            service_summary=service_summary,
            subtotal=payment.subtotal,
            discount=payment.discount_amount,
            platform_fee=payment.platform_fee,
            tax=Decimal("0.00"),
            total_amount=payment.total_amount,
            status=InvoiceStatus.PAID if payment.status == "COMPLETED" else InvoiceStatus.ISSUED,
        )
        return invoice
