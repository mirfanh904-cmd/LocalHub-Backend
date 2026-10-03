from decimal import Decimal
import uuid
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from payments.models import (
    Wallet,
    WalletTransaction,
    PromoCode,
    PromoDiscountType,
    Payment,
    PaymentMethod,
    PaymentStatus,
    EscrowHold,
    EscrowStatus,
    CommissionRecord,
    ProfessionalPayout,
    PayoutStatus,
    PayoutMethod,
    RefundRequest,
    RefundStatus,
    Invoice,
    TransactionType,
)
from payments.services import (
    WalletService,
    PaymentService,
    EscrowService,
    CommissionService,
    InvoiceService,
    RefundService,
    PayoutService,
)
from services.models import Service, Category, ServiceGroup
from bookings.models import Booking, BookingStatus, PaymentStatus as BookingPaymentStatus
from accounts.models import Address, ProfessionalProfile

User = get_user_model()


class PaymentsEcosystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.customer = User.objects.create_user(
            email="customer_pay_test@localhub.com",
            password="StrongPassword123!",
            first_name="Alice",
            last_name="Pay",
            role=User.Role.CUSTOMER,
        )
        self.worker_user = User.objects.create_user(
            email="worker_pay_test@localhub.com",
            password="StrongPassword123!",
            first_name="Bob",
            last_name="Pro",
            role=User.Role.PROFESSIONAL,
        )
        self.admin_user = User.objects.create_user(
            email="admin_pay_test@localhub.com",
            password="StrongPassword123!",
            first_name="Admin",
            last_name="Boss",
            role=User.Role.ADMIN,
            is_staff=True,
        )

        self.worker_profile = ProfessionalProfile.objects.create(
            user=self.worker_user,
            professional_title="Master Electrician",
            bio="Certified pro with 8 years experience.",
            hourly_rate=Decimal("450.00"),
        )

        # Service hierarchy
        self.group = ServiceGroup.objects.create(name="Home Repairs", slug="home-repairs")
        self.category = Category.objects.create(name="Electrical", slug="electrical", service_group=self.group)
        self.service = Service.objects.create(
            name="Ceiling Fan Repair",
            slug="ceiling-fan-repair",
            category=self.category,
            starting_price=Decimal("500.00"),
        )

        self.address = Address.objects.create(
            user=self.customer,
            full_name="Alice Pay",
            phone="9876543210",
            house_name="Apt 101",
            area="Koramangala",
            city="Bangalore",
            postal_code="560034",
        )

        self.booking = Booking.objects.create(
            booking_number="BK-TEST-PAY-01",
            customer=self.customer,
            worker=self.worker_user,
            service=self.service,
            address=self.address,
            booking_date=timezone.now().date(),
            start_time="10:00:00",
            end_time="11:30:00",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            status=BookingStatus.CONFIRMED,
        )

    def test_01_wallet_creation_and_atomic_ledger(self):
        wallet = WalletService.get_or_create_wallet(self.customer)
        self.assertEqual(wallet.current_balance, Decimal("0.00"))

        # Credit wallet
        txn = WalletService.credit_wallet(
            user=self.customer,
            amount=Decimal("1500.00"),
            transaction_type=TransactionType.WALLET_TOPUP,
            reference_id="TOP-001",
            description="Initial top-up",
        )
        self.assertEqual(txn.amount, Decimal("1500.00"))
        wallet.refresh_from_db()
        self.assertEqual(wallet.current_balance, Decimal("1500.00"))

        # Debit wallet
        txn_debit = WalletService.debit_wallet(
            user=self.customer,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.WALLET_DEBIT,
            reference_id="PAY-001",
            description="Service payment",
        )
        self.assertEqual(txn_debit.balance_after, Decimal("1000.00"))
        wallet.refresh_from_db()
        self.assertEqual(wallet.current_balance, Decimal("1000.00"))

    def test_02_promo_code_validation_and_calculation(self):
        promo = PromoCode.objects.create(
            code="SAVE20",
            discount_type=PromoDiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            max_discount_amount=Decimal("150.00"),
            min_order_amount=Decimal("300.00"),
            valid_from=timezone.now() - timezone.timedelta(days=1),
            valid_until=timezone.now() + timezone.timedelta(days=10),
            usage_limit=10,
        )

        valid, msg = promo.is_valid(Decimal("500.00"))
        self.assertTrue(valid)
        discount = promo.calculate_discount(Decimal("500.00"))
        self.assertEqual(discount, Decimal("100.00"))  # 20% of 500 = 100

        # Subtotal below min amount
        valid_low, msg_low = promo.is_valid(Decimal("200.00"))
        self.assertFalse(valid_low)

    def test_03_payment_checkout_idempotency_and_wallet_escrow(self):
        WalletService.credit_wallet(
            user=self.customer,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.WALLET_TOPUP,
            reference_id="TOP-002",
            description="Top-up for checkout",
        )

        idempotency_key = "idemp_test_key_123"

        # Process checkout via Wallet
        payment = PaymentService.process_checkout(
            customer=self.customer,
            target_type="booking",
            target_id=str(self.booking.id),
            payment_method=PaymentMethod.WALLET,
            idempotency_key=idempotency_key,
        )

        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(payment.total_amount, Decimal("500.00"))
        self.assertTrue(hasattr(payment, "invoice"))
        self.assertTrue(hasattr(payment, "escrow_hold"))
        self.assertEqual(payment.escrow_hold.status, EscrowStatus.HELD)

        # Re-running with same idempotency key should return same payment
        duplicate_payment = PaymentService.process_checkout(
            customer=self.customer,
            target_type="booking",
            target_id=str(self.booking.id),
            payment_method=PaymentMethod.WALLET,
            idempotency_key=idempotency_key,
        )
        self.assertEqual(payment.id, duplicate_payment.id)

    def test_04_escrow_release_on_booking_completion_with_commission(self):
        # Checkout first
        PaymentService.process_checkout(
            customer=self.customer,
            target_type="booking",
            target_id=str(self.booking.id),
            payment_method=PaymentMethod.ONLINE,
            idempotency_key="idemp_online_test_456",
        )

        # Worker wallet starts with 0 available
        worker_wallet = WalletService.get_or_create_wallet(self.worker_user)
        self.assertEqual(worker_wallet.current_balance, Decimal("0.00"))

        # Release escrow
        released = EscrowService.release_booking_escrow(self.booking)
        self.assertTrue(released)

        worker_wallet.refresh_from_db()
        # 10% commission on 500 = 50. Net earning = 450.
        self.assertEqual(worker_wallet.current_balance, Decimal("450.00"))

        comm_record = CommissionRecord.objects.get(booking=self.booking)
        self.assertEqual(comm_record.commission_amount, Decimal("50.00"))
        self.assertEqual(comm_record.net_earning, Decimal("450.00"))
        self.assertTrue(comm_record.is_settled)

    def test_05_refund_request_and_admin_approval(self):
        payment = PaymentService.process_checkout(
            customer=self.customer,
            target_type="booking",
            target_id=str(self.booking.id),
            payment_method=PaymentMethod.ONLINE,
            idempotency_key="idemp_refund_test_789",
        )

        customer_wallet = WalletService.get_or_create_wallet(self.customer)
        initial_customer_bal = customer_wallet.current_balance

        # Customer requests refund
        refund_req = RefundService.request_refund(
            customer=self.customer,
            payment_id=str(payment.id),
            amount=Decimal("500.00"),
            reason="Service was cancelled prior to arrival.",
        )
        self.assertEqual(refund_req.status, RefundStatus.PENDING)

        # Admin approves refund
        RefundService.process_refund_action(
            refund_request=refund_req,
            action="APPROVE",
            admin_user=self.admin_user,
            admin_notes="Approved full refund.",
        )

        refund_req.refresh_from_db()
        self.assertEqual(refund_req.status, RefundStatus.COMPLETED)

        customer_wallet.refresh_from_db()
        self.assertEqual(customer_wallet.current_balance, initial_customer_bal + Decimal("500.00"))

    def test_06_professional_payout_lifecycle(self):
        # Give worker ₹2,000 available balance
        WalletService.credit_wallet(
            user=self.worker_user,
            amount=Decimal("2000.00"),
            transaction_type=TransactionType.EARNING_CREDIT,
            reference_id="EARN-TEST-1",
            description="Completed electrical jobs",
        )

        # Request ₹1,000 payout
        payout = PayoutService.request_payout(
            professional=self.worker_user,
            amount=Decimal("1000.00"),
            payout_method=PayoutMethod.UPI,
            account_details={"upi_id": "bob@okhdfcbank"},
        )
        self.assertEqual(payout.status, PayoutStatus.REQUESTED)

        worker_wallet = WalletService.get_or_create_wallet(self.worker_user)
        self.assertEqual(worker_wallet.current_balance, Decimal("1000.00"))
        self.assertEqual(worker_wallet.pending_balance, Decimal("1000.00"))

        # Admin completes payout
        PayoutService.process_payout_action(
            payout=payout,
            action="COMPLETE",
            admin_user=self.admin_user,
            admin_notes="Settlement transfer reference #UTR998822",
        )
        payout.refresh_from_db()
        self.assertEqual(payout.status, PayoutStatus.COMPLETED)
        worker_wallet.refresh_from_db()
        self.assertEqual(worker_wallet.pending_balance, Decimal("0.00"))

    def test_07_rest_api_endpoints(self):
        self.client.force_authenticate(user=self.customer)

        # GET Wallet
        res = self.client.get("/api/v1/payments/wallet/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("current_balance", res.data)

        # POST Topup
        res_topup = self.client.post("/api/v1/payments/wallet/topup/", {"amount": "500.00"})
        self.assertEqual(res_topup.status_code, status.HTTP_200_OK)

        # GET Invoices
        res_inv = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(res_inv.status_code, status.HTTP_200_OK)

        # Worker Earnings API
        self.client.force_authenticate(user=self.worker_user)
        res_earn = self.client.get("/api/v1/payments/worker/earnings/")
        self.assertEqual(res_earn.status_code, status.HTTP_200_OK)
        self.assertIn("total_net_earnings", res_earn.data)

        # Admin Financial Overview API
        self.client.force_authenticate(user=self.admin_user)
        res_admin = self.client.get("/api/v1/admin/financials/overview/")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertIn("total_platform_revenue", res_admin.data)
