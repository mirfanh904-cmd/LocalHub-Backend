from decimal import Decimal
from datetime import date, time, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from accounts.models import User, ProfessionalProfile, Skill
from tasks.models import Task, TaskCategory, TaskApplication, TaskStatus, ApplicationStatus
from tasks.services import TaskService, TaskApplicationService, SmartMatchingService


class TaskMarketplaceTests(TestCase):

    def setUp(self):
        # 1. Create Customer User
        self.customer = User.objects.create_user(
            email="customer.test@localhub.com",
            first_name="Test",
            last_name="Customer",
            role=User.Role.CUSTOMER,
            password="Password@123",
        )

        # 2. Create Professional User 1
        self.pro1_user = User.objects.create_user(
            email="pro1.test@localhub.com",
            first_name="Pro",
            last_name="One",
            role=User.Role.PROFESSIONAL,
            password="Password@123",
        )
        self.pro1_profile = ProfessionalProfile.objects.create(
            user=self.pro1_user,
            professional_title="Master Electrician",
            experience_years=5,
            hourly_rate=Decimal("299.00"),
            average_rating=Decimal("4.90"),
            reviews_count=20,
        )

        # 3. Create Professional User 2
        self.pro2_user = User.objects.create_user(
            email="pro2.test@localhub.com",
            first_name="Pro",
            last_name="Two",
            role=User.Role.PROFESSIONAL,
            password="Password@123",
        )
        self.pro2_profile = ProfessionalProfile.objects.create(
            user=self.pro2_user,
            professional_title="Plumbing Specialist",
            experience_years=3,
            hourly_rate=Decimal("349.00"),
            average_rating=Decimal("4.70"),
            reviews_count=10,
        )

        # 4. Create Category & Skills
        self.skill_electrical = Skill.objects.create(name="Electrical Repair Test", slug="electrical-repair-test")
        self.pro1_profile.skills.add(self.skill_electrical)

        self.category = TaskCategory.objects.create(
            name="Electrical Work",
            slug="electrical-work",
            description="All electrical tasks",
        )
        self.category.skills.add(self.skill_electrical)

    def test_task_creation_and_defaults(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Fix Living Room Chandelier",
            description="Need ceiling mount and wiring inspection.",
            budget=Decimal("500.00"),
            preferred_date=date.today() + timedelta(days=2),
            preferred_time=time(10, 0),
            city="Kochi",
            postal_code="682036",
        )
        self.assertTrue(task.task_number.startswith("TSK-"))
        self.assertEqual(task.status, TaskStatus.OPEN)
        self.assertEqual(task.customer, self.customer)
        self.assertEqual(task.budget, Decimal("500.00"))
        self.assertEqual(task.status_history.count(), 1)

    def test_invalid_budget_rejected(self):
        with self.assertRaises(ValidationError):
            TaskService.create_task(
                customer=self.customer,
                category=self.category,
                title="Invalid Budget Task",
                description="Zero budget test.",
                budget=Decimal("0.00"),
                preferred_date=date.today(),
                preferred_time=time(10, 0),
                city="Kochi",
                postal_code="682036",
            )

    def test_professional_application_submission(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Switchboard repair",
            description="Burnt switch replacement.",
            budget=Decimal("300.00"),
            preferred_date=date.today() + timedelta(days=1),
            preferred_time=time(14, 0),
            city="Kochi",
            postal_code="682036",
        )

        app = TaskApplicationService.apply_to_task(
            task=task,
            professional=self.pro1_user,
            proposed_price=Decimal("250.00"),
            proposal="I can fix this within 30 minutes with certified safety tools.",
            estimated_duration="30 mins",
        )

        self.assertEqual(app.task, task)
        self.assertEqual(app.professional, self.pro1_user)
        self.assertEqual(app.status, ApplicationStatus.PENDING)
        self.assertEqual(task.applications.count(), 1)

    def test_customer_cannot_apply_to_own_task(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Self application test",
            description="Test description",
            budget=Decimal("200.00"),
            preferred_date=date.today(),
            preferred_time=time(12, 0),
            city="Kochi",
            postal_code="682036",
        )

        # Set customer role as professional to test self-bidding restriction
        self.customer.role = User.Role.PROFESSIONAL
        self.customer.save()

        with self.assertRaises(ValidationError):
            TaskApplicationService.apply_to_task(
                task=task,
                professional=self.customer,
                proposed_price=Decimal("150.00"),
                proposal="Self bid",
            )

    def test_duplicate_application_prevention(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Duplicate bid test",
            description="Test description",
            budget=Decimal("400.00"),
            preferred_date=date.today(),
            preferred_time=time(12, 0),
            city="Kochi",
            postal_code="682036",
        )

        TaskApplicationService.apply_to_task(
            task=task,
            professional=self.pro1_user,
            proposed_price=Decimal("350.00"),
            proposal="First application",
        )

        with self.assertRaises(ValidationError):
            TaskApplicationService.apply_to_task(
                task=task,
                professional=self.pro1_user,
                proposed_price=Decimal("300.00"),
                proposal="Duplicate second application",
            )

    def test_atomic_applicant_selection_and_competing_rejections(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="House rewiring job",
            description="Complete rewiring",
            budget=Decimal("2000.00"),
            preferred_date=date.today() + timedelta(days=3),
            preferred_time=time(9, 0),
            city="Kochi",
            postal_code="682036",
        )

        # Bid 1 by Pro 1
        app1 = TaskApplicationService.apply_to_task(
            task=task,
            professional=self.pro1_user,
            proposed_price=Decimal("1800.00"),
            proposal="Pro 1 bid",
        )

        # Bid 2 by Pro 2
        app2 = TaskApplicationService.apply_to_task(
            task=task,
            professional=self.pro2_user,
            proposed_price=Decimal("1900.00"),
            proposal="Pro 2 bid",
        )

        # Customer selects Pro 1
        assigned_task = TaskApplicationService.select_applicant(
            task=task,
            application=app1,
            customer=self.customer,
        )

        # Assertions
        self.assertEqual(assigned_task.status, TaskStatus.ASSIGNED)
        self.assertEqual(assigned_task.assigned_professional, self.pro1_user)
        self.assertEqual(assigned_task.accepted_application, app1)

        # Reload applications from DB
        app1.refresh_from_db()
        app2.refresh_from_db()

        self.assertEqual(app1.status, ApplicationStatus.ACCEPTED)
        self.assertEqual(app2.status, ApplicationStatus.REJECTED)
        self.assertEqual(assigned_task.status_history.count(), 2)

    def test_task_lifecycle_start_and_completion(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Fan installation",
            description="Mount fan",
            budget=Decimal("300.00"),
            preferred_date=date.today(),
            preferred_time=time(11, 0),
            city="Kochi",
            postal_code="682036",
        )

        app = TaskApplicationService.apply_to_task(
            task=task,
            professional=self.pro1_user,
            proposed_price=Decimal("300.00"),
            proposal="I will install neatly",
        )

        TaskApplicationService.select_applicant(task=task, application=app, customer=self.customer)

        # 1. Pro 1 starts task
        started_task = TaskService.start_task(task, self.pro1_user)
        self.assertEqual(started_task.status, TaskStatus.IN_PROGRESS)

        # 2. Pro 1 completes task
        completed_task = TaskService.complete_task(task, self.pro1_user)
        self.assertEqual(completed_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(completed_task.completed_at)

    def test_invalid_state_transition_prevented(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="State machine validation",
            description="Description",
            budget=Decimal("500.00"),
            preferred_date=date.today(),
            preferred_time=time(10, 0),
            city="Kochi",
            postal_code="682036",
        )

        # Trying to complete an OPEN task before assigning & starting
        with self.assertRaises(ValidationError):
            TaskService.complete_task(task, self.pro1_user)

    def test_application_withdrawal(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Withdrawal test",
            description="Description",
            budget=Decimal("500.00"),
            preferred_date=date.today(),
            preferred_time=time(10, 0),
            city="Kochi",
            postal_code="682036",
        )

        app = TaskApplicationService.apply_to_task(
            task=task,
            professional=self.pro1_user,
            proposed_price=Decimal("450.00"),
            proposal="Proposal",
        )

        withdrawn = TaskApplicationService.withdraw_application(app, self.pro1_user)
        self.assertEqual(withdrawn.status, ApplicationStatus.WITHDRAWN)

    def test_smart_matching_signals(self):
        task = TaskService.create_task(
            customer=self.customer,
            category=self.category,
            title="Electrical smart match",
            description="Description",
            budget=Decimal("500.00"),
            preferred_date=date.today(),
            preferred_time=time(10, 0),
            city="Kochi",
            postal_code="682036",
        )

        matches = SmartMatchingService.get_matching_professionals(task, limit=5)
        self.assertTrue(len(matches) > 0)
        # Pro 1 (has electrical skill) should score higher than Pro 2 (plumbing)
        self.assertEqual(matches[0]["professional_id"], self.pro1_user.id)
        self.assertTrue(matches[0]["match_score"] > matches[1]["match_score"])
