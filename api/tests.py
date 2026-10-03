from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from services.models import ServiceGroup, Category, Service
from accounts.models import ProfessionalProfile, Address
from notifications.models import Notification
from decimal import Decimal

User = get_user_model()


class APISprint6Tests(TestCase):

    def setUp(self):
        # Admin user
        self.admin_user = User.objects.create_superuser(
            email="admin_api@localhub.com",
            password="pwd",
            first_name="Admin",
            last_name="User",
            role="ADMIN"
        )

        # Customer user
        self.customer_user = User.objects.create_user(
            email="customer_api@localhub.com",
            password="pwd",
            first_name="Customer",
            last_name="User",
            role="CUSTOMER"
        )

        # Worker user
        self.worker_user = User.objects.create_user(
            email="worker_api@localhub.com",
            password="pwd",
            first_name="Worker",
            last_name="User",
            role="PROFESSIONAL"
        )
        self.worker_profile = ProfessionalProfile.objects.create(
            user=self.worker_user,
            experience_years=4,
            professional_title="Master Electrician",
            availability_status="available",
        )
        from verification.models import ProfessionalVerification, VerificationStatus
        ProfessionalVerification.objects.update_or_create(
            professional=self.worker_profile,
            defaults={"status": VerificationStatus.APPROVED}
        )

        self.group = ServiceGroup.objects.create(
            name="Home Repair", slug="home-repair", theme_color="#2563EB"
        )
        self.category = Category.objects.create(
            name="Electrical", slug="electrical", service_group=self.group
        )
        self.service = Service.objects.create(
            category=self.category,
            name="Wiring Repair",
            slug="wiring-repair",
            starting_price=Decimal("99.00")
        )

        self.client = APIClient()

    def test_notifications_api_endpoints(self):
        self.client.force_authenticate(user=self.customer_user)
        Notification.objects.create(
            user=self.customer_user,
            title="System Alert",
            message="Welcome to LocalHub!"
        )

        # List Notifications
        res = self.client.get("/api/v1/notifications/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Unread Count Endpoint
        res = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("unread_count", res.json())
        self.assertEqual(res.json()["unread_count"], 1)

    def test_worker_api_permissions_and_endpoints(self):
        # Customer should be forbidden from worker endpoints
        self.client.force_authenticate(user=self.customer_user)
        res = self.client.get("/api/v1/worker/bookings/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Verified worker should be allowed
        self.client.force_authenticate(user=self.worker_user)
        res = self.client.get("/api/v1/worker/bookings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_admin_dashboard_and_crud_apis(self):
        # Non-admin forbidden
        self.client.force_authenticate(user=self.customer_user)
        res = self.client.get("/api/v1/admin/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Admin allowed
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get("/api/v1/admin/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("total_users", data)
        self.assertIn("total_categories", data)

        # Service Group CRUD
        res = self.client.get("/api/v1/service-groups/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Categories CRUD
        res = self.client.get("/api/v1/categories/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_favourites_api(self):
        self.client.force_authenticate(user=self.customer_user)
        
        # Toggle favourite service
        res = self.client.post(f"/api/v1/favourites/services/{self.service.id}/toggle/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["is_favourited"])

        # List favourite services
        res = self.client.get("/api/v1/favourites/services/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
