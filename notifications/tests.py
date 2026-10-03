from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from services.models import Category, Service, ServiceGroup
from bookings.models import Booking, BookingStatus
from bookings.services import BookingService
from accounts.models import Address
from notifications.models import Notification, NotificationType
from notifications.services import NotificationService
from notifications.selectors import NotificationSelector
from notifications.context_processors import unread_notifications_count
from decimal import Decimal
import datetime

User = get_user_model()


class NotificationSystemTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust@localhub.com",
            password="pwd",
            first_name="Customer",
            last_name="Test",
            role="CUSTOMER"
        )
        self.worker = User.objects.create_user(
            email="worker@localhub.com",
            password="pwd",
            first_name="Worker",
            last_name="Test",
            role="PROFESSIONAL"
        )
        self.group = ServiceGroup.objects.create(
            name="G1", slug="g1", theme_color="#fff"
        )
        self.category = Category.objects.create(
            name="C1", slug="c1", service_group=self.group
        )
        self.service = Service.objects.create(
            category=self.category,
            name="S1",
            slug="s1",
            starting_price=Decimal("50.00")
        )
        self.address = Address.objects.create(
            user=self.customer,
            full_name="A1",
            phone="123456",
            house_name="1A",
            area="Street 1",
            city="City",
            state="State",
            country="Country",
            postal_code="1000"
        )
        self.client = Client()
        self.client.force_login(self.customer)

    def test_notification_creation_and_unread_counts(self):
        # Initial unread count should be 0
        self.assertEqual(NotificationSelector.unread_count(self.customer), 0)

        # Trigger notification through booking creation
        booking = BookingService.create({
            "customer": self.customer,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today(),
            "start_time": datetime.time(9, 0),
            "end_time": datetime.time(11, 0),
            "subtotal": Decimal("50.00"),
            "total_amount": Decimal("50.00"),
        })

        self.assertEqual(NotificationSelector.unread_count(self.customer), 1)

        # Retrieve notifications
        notifs = NotificationSelector.user_notifications(self.customer)
        self.assertEqual(notifs.count(), 1)
        notif = notifs.first()
        self.assertEqual(notif.notification_type, NotificationType.BOOKING)

        # Mark as read
        NotificationService.mark_as_read(notif.id, self.customer)
        self.assertEqual(NotificationSelector.unread_count(self.customer), 0)

    def test_status_transitions_and_unread_count_increases(self):
        booking = BookingService.create({
            "customer": self.customer,
            "service": self.service,
            "address": self.address,
            "booking_date": datetime.date.today(),
            "start_time": datetime.time(9, 0),
            "end_time": datetime.time(11, 0),
            "subtotal": Decimal("50.00"),
            "total_amount": Decimal("50.00"),
        })

        # Transition status
        BookingService.change_status(
            booking,
            BookingStatus.WORKER_ASSIGNED,
            changed_by=self.customer,
            source="customer"
        )

        # Expected: 1 for creation, 1 for WORKER_ASSIGNED status transition
        self.assertEqual(NotificationSelector.unread_count(self.customer), 2)

        # Bulk mark read
        NotificationService.mark_all_as_read(self.customer)
        self.assertEqual(NotificationSelector.unread_count(self.customer), 0)

    def test_context_processor(self):
        # Verify context processor is lightweight and returns unread count
        req = type("Request", (object,), {"user": self.customer})
        data = unread_notifications_count(req)
        self.assertIn("unread_notifications_count", data)
        self.assertEqual(data["unread_notifications_count"], 0)

        # Add an unread notification
        NotificationService.create_notification(
            user=self.customer,
            notification_type=NotificationType.SYSTEM,
            title="System Alert",
            message="Test Msg"
        )

        data = unread_notifications_count(req)
        self.assertEqual(data["unread_notifications_count"], 1)

    def test_views_status_codes(self):
        # Create a test notification
        notif = NotificationService.create_notification(
            user=self.customer,
            notification_type=NotificationType.SYSTEM,
            title="T1",
            message="M1"
        )

        # Service mark read
        success = NotificationService.mark_as_read(notif.id, self.customer)
        self.assertTrue(success)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

        # Service mark all read
        NotificationService.create_notification(
            user=self.customer,
            notification_type=NotificationType.SYSTEM,
            title="T2",
            message="M2"
        )
        NotificationService.mark_all_as_read(self.customer)
        self.assertEqual(NotificationSelector.unread_count(self.customer), 0)
