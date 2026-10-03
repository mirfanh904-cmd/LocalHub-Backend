from django.test import TestCase
from django.contrib.auth import get_user_model
from services.models import Category, Service, ServiceGroup
from bookings.models import Booking, BookingStatus, Review
from bookings.services import BookingService, ReviewService
from accounts.models import Address, ProfessionalProfile
from decimal import Decimal
import datetime

User = get_user_model()


class ReviewSystemAndAggregationTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust_rev@localhub.com",
            password="pwd",
            first_name="Customer",
            last_name="Review",
            role="CUSTOMER"
        )
        self.worker = User.objects.create_user(
            email="worker_rev@localhub.com",
            password="pwd",
            first_name="Worker",
            last_name="Review",
            role="PROFESSIONAL"
        )
        self.profile = ProfessionalProfile.objects.create(
            user=self.worker,
            experience_years=3,
            professional_title="Plumbing Pro",
            availability_status="available",
        )
        self.group = ServiceGroup.objects.create(
            name="Group", slug="group", theme_color="#fff"
        )
        self.category = Category.objects.create(
            name="Cat", slug="cat", service_group=self.group
        )
        self.service = Service.objects.create(
            category=self.category,
            name="Plumbing",
            slug="plumbing",
            starting_price=Decimal("150.00")
        )
        self.address = Address.objects.create(
            user=self.customer,
            full_name="Addr",
            phone="12345",
            house_name="10B",
            area="Plaza",
            city="Metro",
            state="Region",
            country="Country",
            postal_code="2000"
        )

    def test_review_creation_and_aggregations(self):
        # Create a booking
        booking = BookingService.create({
            "customer": self.customer,
            "worker": self.worker,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today(),
            "start_time": datetime.time(14, 0),
            "end_time": datetime.time(16, 0),
            "subtotal": Decimal("150.00"),
            "total_amount": Decimal("150.00"),
        })

        # Transitions to COMPLETED
        BookingService.change_status(booking, BookingStatus.WORKER_ASSIGNED, self.worker, "worker")
        BookingService.change_status(booking, BookingStatus.ON_THE_WAY, self.worker, "worker")
        BookingService.change_status(booking, BookingStatus.ARRIVED, self.worker, "worker")
        BookingService.change_status(booking, BookingStatus.STARTED, self.worker, "worker")
        BookingService.change_status(booking, BookingStatus.IN_PROGRESS, self.worker, "worker")
        BookingService.change_status(booking, BookingStatus.COMPLETED, self.worker, "worker")

        # Confirm aggregates are 0 initially
        self.assertEqual(self.service.average_rating, Decimal("0.00"))
        self.assertEqual(self.service.reviews_count, 0)
        self.assertEqual(self.profile.average_rating, Decimal("0.00"))
        self.assertEqual(self.profile.reviews_count, 0)

        # Submit 5-star review
        review = ReviewService.create_review(
            booking=booking,
            customer=self.customer,
            rating=5,
            comment="Awesome!"
        )

        self.service.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.service.average_rating, Decimal("5.00"))
        self.assertEqual(self.service.reviews_count, 1)
        self.assertEqual(self.profile.average_rating, Decimal("5.00"))
        self.assertEqual(self.profile.reviews_count, 1)
        self.assertTrue(booking.is_reviewed)

        # Try to review again - should fail
        with self.assertRaises(ValueError):
            ReviewService.create_review(
                booking=booking,
                customer=self.customer,
                rating=4
            )


class ReviewReplyAndReportTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust_rep@localhub.com",
            password="pwd",
            first_name="Customer",
            last_name="Test",
            role="CUSTOMER"
        )
        self.worker = User.objects.create_user(
            email="worker_rep@localhub.com",
            password="pwd",
            first_name="Worker",
            last_name="Test",
            role="PROFESSIONAL"
        )
        self.other_worker = User.objects.create_user(
            email="other_worker@localhub.com",
            password="pwd",
            first_name="Other",
            last_name="Worker",
            role="PROFESSIONAL"
        )
        self.admin = User.objects.create_superuser(
            email="admin_rep@localhub.com",
            password="pwd",
            first_name="Admin",
            last_name="Test",
            role="ADMIN"
        )
        self.group = ServiceGroup.objects.create(name="Group2", slug="group2", theme_color="#fff")
        self.category = Category.objects.create(name="Cat2", slug="cat2", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="Electrical", slug="electrical", starting_price=Decimal("100.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

        self.booking = BookingService.create({
            "customer": self.customer,
            "worker": self.worker,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today(),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(11, 0),
            "subtotal": Decimal("100.00"),
            "total_amount": Decimal("100.00"),
        })
        BookingService.change_status(self.booking, BookingStatus.WORKER_ASSIGNED, self.worker, "worker")
        BookingService.change_status(self.booking, BookingStatus.ON_THE_WAY, self.worker, "worker")
        BookingService.change_status(self.booking, BookingStatus.ARRIVED, self.worker, "worker")
        BookingService.change_status(self.booking, BookingStatus.STARTED, self.worker, "worker")
        BookingService.change_status(self.booking, BookingStatus.IN_PROGRESS, self.worker, "worker")
        BookingService.change_status(self.booking, BookingStatus.COMPLETED, self.worker, "worker")
        self.review = ReviewService.create_review(self.booking, self.customer, 5, "Great work!")


    def test_review_reply_by_assigned_worker(self):
        from bookings.services import ReviewReplyService
        from django.core.exceptions import ValidationError

        # Assigned worker can reply
        reply = ReviewReplyService.reply_to_review(
            review=self.review,
            professional_user=self.worker,
            comment="Thank you for your feedback!"
        )
        self.assertEqual(reply.comment, "Thank you for your feedback!")
        self.assertEqual(reply.professional, self.worker)

        # Non-assigned worker cannot reply
        with self.assertRaises(ValidationError):
            ReviewReplyService.reply_to_review(
                review=self.review,
                professional_user=self.other_worker,
                comment="Imposter reply"
            )

    def test_review_reporting_and_moderation(self):
        from bookings.services import ReviewReportService
        from bookings.models import ReportReason, ReportStatus
        from django.core.exceptions import ValidationError

        # Customer cannot report their own review
        with self.assertRaises(ValidationError):
            ReviewReportService.report_review(
                review=self.review,
                reporter_user=self.customer,
                reason=ReportReason.SPAM
            )

        # Other user can report review
        report = ReviewReportService.report_review(
            review=self.review,
            reporter_user=self.worker,
            reason=ReportReason.HARASSMENT,
            description="Inappropriate language"
        )
        self.assertEqual(report.status, ReportStatus.PENDING)

        # Duplicate reporting is blocked
        with self.assertRaises(ValidationError):
            ReviewReportService.report_review(
                review=self.review,
                reporter_user=self.worker,
                reason=ReportReason.SPAM
            )

        # Admin moderates report
        ReviewReportService.moderate_report(report, self.admin, ReportStatus.RESOLVED, "Handled")
        report.refresh_from_db()
        self.assertEqual(report.status, ReportStatus.RESOLVED)


class ComplaintTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust_cmp@localhub.com",
            password="pwd",
            first_name="Customer",
            last_name="Cmp",
            role="CUSTOMER"
        )
        self.other_customer = User.objects.create_user(
            email="other_cmp@localhub.com",
            password="pwd",
            first_name="Other",
            last_name="Cmp",
            role="CUSTOMER"
        )
        self.worker = User.objects.create_user(
            email="worker_cmp@localhub.com",
            password="pwd",
            first_name="Worker",
            last_name="Cmp",
            role="PROFESSIONAL"
        )
        self.admin = User.objects.create_superuser(
            email="admin_cmp@localhub.com",
            password="pwd",
            first_name="Admin",
            last_name="Cmp",
            role="ADMIN"
        )
        self.group = ServiceGroup.objects.create(name="Group3", slug="group3", theme_color="#fff")
        self.category = Category.objects.create(name="Cat3", slug="cat3", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="Carpentry", slug="carpentry", starting_price=Decimal("120.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

        self.booking = BookingService.create({
            "customer": self.customer,
            "worker": self.worker,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today(),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(11, 0),
            "subtotal": Decimal("120.00"),
            "total_amount": Decimal("120.00"),
        })

    def test_complaint_lifecycle(self):
        from bookings.services import ComplaintService
        from bookings.models import ComplaintCategory, ComplaintStatus
        from django.core.exceptions import ValidationError

        # Customer filing complaint against their booking
        complaint = ComplaintService.create_complaint(
            customer=self.customer,
            category=ComplaintCategory.SERVICE_QUALITY,
            subject="Job was incomplete",
            description="The carpenter left half the wardrobe unpainted.",
            booking=self.booking,
        )
        self.assertTrue(complaint.complaint_number.startswith("CMP-"))
        self.assertEqual(complaint.professional, self.worker)
        self.assertEqual(complaint.status, ComplaintStatus.PENDING)

        # Other customer cannot file against this booking
        with self.assertRaises(ValidationError):
            ComplaintService.create_complaint(
                customer=self.other_customer,
                category=ComplaintCategory.SERVICE_QUALITY,
                subject="Fake complaint",
                description="Fake",
                booking=self.booking,
            )

        # Admin moves to investigation
        ComplaintService.investigate_complaint(complaint, self.admin, "Contacted worker for statement.")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.UNDER_INVESTIGATION)

        # Admin resolves complaint
        ComplaintService.resolve_complaint(complaint, self.admin, "Refund of 50% issued and worker cautioned.")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.RESOLVED)
        self.assertEqual(complaint.resolved_by, self.admin)
        self.assertIsNotNone(complaint.resolved_at)


class BookingLifecycleAndStateMachineTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(email="cust_lc@localhub.com", password="pwd", first_name="Cust", last_name="LC", role="CUSTOMER")
        self.worker = User.objects.create_user(email="worker_lc@localhub.com", password="pwd", first_name="Work", last_name="LC", role="PROFESSIONAL")
        self.other_worker = User.objects.create_user(email="worker2_lc@localhub.com", password="pwd", first_name="Work2", last_name="LC", role="PROFESSIONAL")
        self.group = ServiceGroup.objects.create(name="LC Group", slug="lc-group", theme_color="#fff")
        self.category = Category.objects.create(name="LC Cat", slug="lc-cat", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="LC Service", slug="lc-service", starting_price=Decimal("200.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

    def test_full_valid_lifecycle_progression(self):
        booking = BookingService.create({
            "customer": self.customer,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=1),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("200.00"),
            "total_amount": Decimal("200.00"),
        })
        self.assertEqual(booking.status, BookingStatus.PENDING)

        # 1. Confirm
        BookingService.confirm(booking, self.customer)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CONFIRMED)

        # 2. Assign worker
        BookingService.assign_worker(booking, self.worker, self.worker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.WORKER_ASSIGNED)
        self.assertEqual(booking.worker, self.worker)

        # 3. On the way
        BookingService.on_the_way(booking, self.worker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.ON_THE_WAY)

        # 4. Arrived
        BookingService.arrived(booking, self.worker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.ARRIVED)

        # 5. Started
        BookingService.started(booking, self.worker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.STARTED)

        # 6. In progress
        BookingService.in_progress(booking, self.worker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.IN_PROGRESS)

        # 7. Completed
        BookingService.complete(booking, self.worker)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.COMPLETED)
        self.assertIsNotNone(booking.completed_at)

        # Audit history verified
        history_count = booking.status_history.count()
        self.assertGreaterEqual(history_count, 7)

    def test_invalid_status_transitions_rejected(self):
        booking = BookingService.create({
            "customer": self.customer,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=1),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("200.00"),
            "total_amount": Decimal("200.00"),
        })

        # Cannot jump from PENDING to COMPLETED directly
        with self.assertRaises(ValueError):
            BookingService.change_status(booking, BookingStatus.COMPLETED)

        # Complete booking
        BookingService.change_status(booking, BookingStatus.CONFIRMED)
        BookingService.change_status(booking, BookingStatus.WORKER_ASSIGNED)
        BookingService.change_status(booking, BookingStatus.ON_THE_WAY)
        BookingService.change_status(booking, BookingStatus.ARRIVED)
        BookingService.change_status(booking, BookingStatus.STARTED)
        BookingService.change_status(booking, BookingStatus.IN_PROGRESS)
        BookingService.change_status(booking, BookingStatus.COMPLETED)

        # Cannot move COMPLETED booking back to PENDING or IN_PROGRESS
        with self.assertRaises(ValueError):
            BookingService.change_status(booking, BookingStatus.IN_PROGRESS)

    def test_cancellation_workflow_and_terminal_state(self):
        booking = BookingService.create({
            "customer": self.customer,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=1),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("200.00"),
            "total_amount": Decimal("200.00"),
        })
        BookingService.cancel(booking, self.customer, "Schedule changed", "customer")
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertIsNotNone(booking.cancelled_at)

        # Cannot move CANCELLED booking back to CONFIRMED
        with self.assertRaises(ValueError):
            BookingService.change_status(booking, BookingStatus.CONFIRMED)


class WorkerAssignmentConcurrencyTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(email="cust_assign@localhub.com", password="pwd", first_name="Cust", last_name="Assign", role="CUSTOMER")
        self.worker1 = User.objects.create_user(email="worker1_assign@localhub.com", password="pwd", first_name="W1", last_name="Assign", role="PROFESSIONAL")
        self.worker2 = User.objects.create_user(email="worker2_assign@localhub.com", password="pwd", first_name="W2", last_name="Assign", role="PROFESSIONAL")
        self.group = ServiceGroup.objects.create(name="Assign Group", slug="assign-group", theme_color="#fff")
        self.category = Category.objects.create(name="Assign Cat", slug="assign-cat", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="Assign Service", slug="assign-service", starting_price=Decimal("100.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

    def test_worker_assignment_concurrency_protection(self):
        from django.core.exceptions import ValidationError
        booking = BookingService.create({
            "customer": self.customer,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=1),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("100.00"),
            "total_amount": Decimal("100.00"),
        })

        # First assignment succeeds
        BookingService.assign_worker(booking, self.worker1, self.worker1)
        booking.refresh_from_db()
        self.assertEqual(booking.worker, self.worker1)

        # Attempt to assign a second different worker raises ValidationError
        with self.assertRaises(ValidationError):
            BookingService.assign_worker(booking, self.worker2, self.worker2)


class BookingOTPWorkflowTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(email="cust_otp@localhub.com", password="pwd", first_name="Cust", last_name="OTP", role="CUSTOMER")
        self.worker = User.objects.create_user(email="worker_otp@localhub.com", password="pwd", first_name="Work", last_name="OTP", role="PROFESSIONAL")
        self.group = ServiceGroup.objects.create(name="OTP Group", slug="otp-group", theme_color="#fff")
        self.category = Category.objects.create(name="OTP Cat", slug="otp-cat", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="OTP Service", slug="otp-service", starting_price=Decimal("150.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

        self.booking = BookingService.create({
            "customer": self.customer,
            "worker": self.worker,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=1),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("150.00"),
            "total_amount": Decimal("150.00"),
        })
        BookingService.change_status(self.booking, BookingStatus.WORKER_ASSIGNED, self.worker)
        BookingService.change_status(self.booking, BookingStatus.ON_THE_WAY, self.worker)
        BookingService.change_status(self.booking, BookingStatus.ARRIVED, self.worker)

    def test_otp_generation_and_successful_verification(self):
        from bookings.services import BookingOTPService
        raw_otp = BookingOTPService.generate_otp(self.booking)
        self.assertEqual(len(raw_otp), 6)
        self.assertTrue(raw_otp.isdigit())

        # Check OTP status
        status_info = BookingOTPService.get_otp_status(self.booking)
        self.assertTrue(status_info["is_generated"])
        self.assertFalse(status_info["is_verified"])

        # Worker verifies OTP
        verified = BookingOTPService.verify_otp(self.booking, raw_otp, self.worker)
        self.assertTrue(verified)

        # Booking transitions to STARTED after OTP verification
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.STARTED)

        # Re-verifying raises error
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            BookingOTPService.verify_otp(self.booking, raw_otp, self.worker)

    def test_otp_wrong_attempts_and_lockout(self):
        from bookings.services import BookingOTPService
        from django.core.exceptions import ValidationError
        BookingOTPService.generate_otp(self.booking)

        # Attempt 1 wrong
        with self.assertRaises(ValidationError) as ctx1:
            BookingOTPService.verify_otp(self.booking, "000000", self.worker)
        self.assertIn("2 attempt(s) remaining", str(ctx1.exception))

        # Attempt 2 wrong
        with self.assertRaises(ValidationError) as ctx2:
            BookingOTPService.verify_otp(self.booking, "000000", self.worker)
        self.assertIn("1 attempt(s) remaining", str(ctx2.exception))

        # Attempt 3 wrong - triggers lockout
        with self.assertRaises(ValidationError) as ctx3:
            BookingOTPService.verify_otp(self.booking, "000000", self.worker)
        self.assertIn("locked for 15 minutes", str(ctx3.exception))

        # Attempt 4 blocked by lock
        with self.assertRaises(ValidationError) as ctx4:
            BookingOTPService.verify_otp(self.booking, "123456", self.worker)
        self.assertIn("locked", str(ctx4.exception))


class BookingReschedulingWorkflowTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(email="cust_resched@localhub.com", password="pwd", first_name="Cust", last_name="Resched", role="CUSTOMER")
        self.worker = User.objects.create_user(email="worker_resched@localhub.com", password="pwd", first_name="Work", last_name="Resched", role="PROFESSIONAL")
        self.group = ServiceGroup.objects.create(name="Resched Group", slug="resched-group", theme_color="#fff")
        self.category = Category.objects.create(name="Resched Cat", slug="resched-cat", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="Resched Service", slug="resched-service", starting_price=Decimal("150.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

        self.booking = BookingService.create({
            "customer": self.customer,
            "worker": self.worker,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=2),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("150.00"),
            "total_amount": Decimal("150.00"),
        })
        BookingService.change_status(self.booking, BookingStatus.WORKER_ASSIGNED, self.worker)

    def test_reschedule_request_mutual_acceptance(self):
        from bookings.services import BookingRescheduleService
        from bookings.models import RescheduleStatus

        new_date = datetime.date.today() + datetime.timedelta(days=4)
        new_start = datetime.time(14, 0)
        new_end = datetime.time(16, 0)

        # Customer creates reschedule request
        req = BookingRescheduleService.create_request(
            booking=self.booking,
            requested_by=self.customer,
            requested_date=new_date,
            requested_start_time=new_start,
            requested_end_time=new_end,
            reason="Meeting scheduled at work",
        )
        self.assertEqual(req.status, RescheduleStatus.PENDING)

        # Worker accepts reschedule request
        BookingRescheduleService.respond_request(
            reschedule_request=req,
            user=self.worker,
            action="accept",
            response_note="Accepted new afternoon slot",
        )
        req.refresh_from_db()
        self.assertEqual(req.status, RescheduleStatus.ACCEPTED)

        # Booking schedule updated
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_date, new_date)
        self.assertEqual(self.booking.start_time, new_start)
        self.assertEqual(self.booking.end_time, new_end)

    def test_reschedule_request_rejection(self):
        from bookings.services import BookingRescheduleService
        from bookings.models import RescheduleStatus

        new_date = datetime.date.today() + datetime.timedelta(days=5)
        req = BookingRescheduleService.create_request(
            booking=self.booking,
            requested_by=self.customer,
            requested_date=new_date,
            requested_start_time=datetime.time(9, 0),
            requested_end_time=datetime.time(11, 0),
            reason="Doctor appointment",
        )

        # Worker rejects request
        BookingRescheduleService.respond_request(
            reschedule_request=req,
            user=self.worker,
            action="reject",
            response_note="Already booked at that time slot",
        )
        req.refresh_from_db()
        self.assertEqual(req.status, RescheduleStatus.REJECTED)

        # Original booking schedule remains unchanged
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_date, datetime.date.today() + datetime.timedelta(days=2))


class BookingAPITests(TestCase):

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.customer = User.objects.create_user(email="cust_api@localhub.com", password="password123", first_name="API", last_name="Customer", role="CUSTOMER")
        self.worker = User.objects.create_user(email="worker_api@localhub.com", password="password123", first_name="API", last_name="Worker", role="PROFESSIONAL")
        self.group = ServiceGroup.objects.create(name="API Group", slug="api-group", theme_color="#fff")
        self.category = Category.objects.create(name="API Cat", slug="api-cat", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="API Service", slug="api-service", starting_price=Decimal("150.00"))
        self.address = Address.objects.create(user=self.customer, full_name="Addr", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

        self.booking = BookingService.create({
            "customer": self.customer,
            "worker": self.worker,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today() + datetime.timedelta(days=1),
            "start_time": datetime.time(10, 0),
            "end_time": datetime.time(12, 0),
            "subtotal": Decimal("150.00"),
            "total_amount": Decimal("150.00"),
        })

    def test_otp_api_flow(self):
        # 1. Customer generates OTP
        self.client.force_authenticate(user=self.customer)
        gen_res = self.client.post(f"/api/v1/bookings/{self.booking.booking_number}/otp/generate/")
        self.assertEqual(gen_res.status_code, 200)

        # 2. Get status API
        stat_res = self.client.get(f"/api/v1/bookings/{self.booking.booking_number}/otp/status/")
        self.assertEqual(stat_res.status_code, 200)
        self.assertTrue(stat_res.data["data"]["is_generated"])
        self.assertFalse(stat_res.data["data"]["is_verified"])

        # 3. Worker verifies OTP API
        from bookings.models import BookingOTP
        from bookings.services import BookingOTPService
        # Generate known raw OTP
        raw_otp = BookingOTPService.generate_otp(self.booking)

        self.client.force_authenticate(user=self.worker)
        verify_res = self.client.post(
            f"/api/v1/bookings/{self.booking.booking_number}/otp/verify/",
            data={"otp_code": raw_otp},
            format="json",
        )
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.data["success"])

    def test_reschedule_api_flow(self):
        self.client.force_authenticate(user=self.customer)
        new_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")

        # Create reschedule request
        create_res = self.client.post(
            f"/api/v1/bookings/{self.booking.booking_number}/reschedule/",
            data={
                "requested_date": new_date,
                "requested_start_time": "14:00:00",
                "requested_end_time": "16:00:00",
                "reason": "Doctor visit",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, 201)
        req_id = create_res.data["data"]["id"]

        # Worker responds to reschedule request
        self.client.force_authenticate(user=self.worker)
        resp_res = self.client.post(
            f"/api/v1/bookings/{self.booking.booking_number}/reschedule/{req_id}/respond/",
            data={"action": "accept", "response_note": "Confirmed"},
            format="json",
        )
        self.assertEqual(resp_res.status_code, 200)
        self.assertEqual(resp_res.data["data"]["status"], "accepted")


