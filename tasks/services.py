from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import ProfessionalProfile
from .models import Task, TaskApplication, TaskStatusHistory, TaskStatus, ApplicationStatus


class TaskService:

    @staticmethod
    def generate_task_number():
        year = timezone.now().year
        count = Task.objects.count() + 1
        return f"TSK-{year}-{count:04d}"

    @staticmethod
    @transaction.atomic
    def create_task(customer, category, title, description, budget, preferred_date, preferred_time, city, postal_code, address=None, house_name="", area="", is_draft=False):
        if budget <= Decimal("0.00"):
            raise ValidationError("Task budget must be greater than zero.")

        # Ensure unique task number
        task_number = TaskService.generate_task_number()
        counter = 1
        while Task.objects.filter(task_number=task_number).exists():
            task_number = f"TSK-{timezone.now().year}-{Task.objects.count() + counter:04d}"
            counter += 1

        status = TaskStatus.DRAFT if is_draft else TaskStatus.OPEN

        task = Task.objects.create(
            task_number=task_number,
            customer=customer,
            category=category,
            title=title,
            description=description,
            budget=budget,
            address=address,
            house_name=house_name or (address.house_name if address else ""),
            area=area or (address.area if address else ""),
            city=city or (address.city if address else "Kochi"),
            postal_code=postal_code or (address.postal_code if address else "682001"),
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            status=status,
        )

        TaskStatusHistory.objects.create(
            task=task,
            status=status,
            changed_by=customer,
            note="Task created by customer." if not is_draft else "Task saved as draft.",
            source="customer",
        )

        if status == TaskStatus.OPEN:
            # Send notification
            from notifications.services import NotificationService
            from notifications.models import NotificationType
            NotificationService.create_notification(
                user=customer,
                notification_type=NotificationType.SYSTEM,
                title="Task Published",
                message=f"Your task '{task.title}' ({task.task_number}) is live and accepting applications.",
            )

        return task

    @staticmethod
    @transaction.atomic
    def publish_draft_task(task, customer):
        if task.customer != customer:
            raise ValidationError("You do not have permission to publish this task.")

        if task.status != TaskStatus.DRAFT:
            raise ValidationError(f"Cannot publish task in '{task.get_status_display()}' status.")

        task.status = TaskStatus.OPEN
        task.save(update_fields=["status", "updated_at"])

        TaskStatusHistory.objects.create(
            task=task,
            status=TaskStatus.OPEN,
            changed_by=customer,
            note="Customer published task from draft.",
            source="customer",
        )
        return task

    @staticmethod
    @transaction.atomic
    def cancel_task(task, user, reason=""):
        # Allowed for customer if in DRAFT, OPEN, or ASSIGNED (with reason)
        is_customer = task.customer == user
        is_admin = user.is_staff or getattr(user, "role", None) == "ADMIN"

        if not (is_customer or is_admin):
            raise ValidationError("You do not have permission to cancel this task.")

        if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            raise ValidationError(f"Cannot cancel task already in '{task.get_status_display()}' state.")

        previous_status = task.status
        now = timezone.now()
        task.status = TaskStatus.CANCELLED
        task.cancelled_at = now
        task.cancellation_reason = reason or "Cancelled by user."
        task.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])

        # Auto-reject all pending applications
        task.applications.filter(status=ApplicationStatus.PENDING).update(status=ApplicationStatus.REJECTED)

        TaskStatusHistory.objects.create(
            task=task,
            status=TaskStatus.CANCELLED,
            changed_by=user,
            note=f"Task cancelled from {previous_status}. Reason: {task.cancellation_reason}",
            source="admin" if is_admin else "customer",
        )

        from notifications.services import NotificationService
        from notifications.models import NotificationType

        # Notify assigned pro if any
        if task.assigned_professional:
            NotificationService.create_notification(
                user=task.assigned_professional,
                notification_type=NotificationType.SYSTEM,
                title="Assigned Task Cancelled",
                message=f"Task '{task.title}' ({task.task_number}) was cancelled by the customer.",
            )

        return task

    @staticmethod
    @transaction.atomic
    def start_task(task, professional):
        if task.assigned_professional != professional and not professional.is_staff:
            raise ValidationError("Only the assigned professional can start this task.")

        if task.status != TaskStatus.ASSIGNED:
            raise ValidationError(f"Cannot start task with status '{task.get_status_display()}'. Task must be in ASSIGNED state.")

        task.status = TaskStatus.IN_PROGRESS
        task.save(update_fields=["status", "updated_at"])

        TaskStatusHistory.objects.create(
            task=task,
            status=TaskStatus.IN_PROGRESS,
            changed_by=professional,
            note="Assigned professional started work on the task.",
            source="professional",
        )

        from notifications.services import NotificationService
        from notifications.models import NotificationType
        NotificationService.create_notification(
            user=task.customer,
            notification_type=NotificationType.SYSTEM,
            title="Work In Progress",
            message=f"Professional {professional.full_name} has started work on your task '{task.title}'.",
        )

        return task

    @staticmethod
    @transaction.atomic
    def complete_task(task, professional):
        if task.assigned_professional != professional and not professional.is_staff:
            raise ValidationError("Only the assigned professional can complete this task.")

        if task.status != TaskStatus.IN_PROGRESS:
            raise ValidationError(f"Cannot complete task with status '{task.get_status_display()}'. Task must be IN_PROGRESS.")

        now = timezone.now()
        task.status = TaskStatus.COMPLETED
        task.completed_at = now
        task.save(update_fields=["status", "completed_at", "updated_at"])

        TaskStatusHistory.objects.create(
            task=task,
            status=TaskStatus.COMPLETED,
            changed_by=professional,
            note="Assigned professional marked task as completed.",
            source="professional",
        )

        try:
            from payments.services import EscrowService
            EscrowService.release_task_escrow(task)
        except Exception:
            pass

        from notifications.services import NotificationService
        from notifications.models import NotificationType
        NotificationService.create_notification(
            user=task.customer,
            notification_type=NotificationType.SYSTEM,
            title="Task Completed",
            message=f"Task '{task.title}' ({task.task_number}) has been completed by {professional.full_name}.",
        )

        return task


class TaskApplicationService:

    @staticmethod
    @transaction.atomic
    def apply_to_task(task, professional, proposed_price, proposal, estimated_duration=""):
        # 1. Validate Professional role
        if getattr(professional, "role", None) != "PROFESSIONAL" and not professional.is_staff:
            raise ValidationError("Only registered professionals can submit bids for marketplace tasks.")

        # 2. Cannot apply to own task
        if task.customer == professional:
            raise ValidationError("You cannot apply to your own task.")

        # 3. Check Task is OPEN
        if task.status != TaskStatus.OPEN:
            raise ValidationError(f"Cannot apply to task in '{task.get_status_display()}' status. Task is no longer accepting bids.")

        # 4. Check Proposed Price
        if proposed_price <= Decimal("0.00"):
            raise ValidationError("Proposed price must be greater than zero.")

        # 5. Check Duplicate Application
        if TaskApplication.objects.filter(task=task, professional=professional).exists():
            raise ValidationError("You have already submitted an application for this task.")

        application = TaskApplication.objects.create(
            task=task,
            professional=professional,
            proposed_price=proposed_price,
            proposal=proposal,
            estimated_duration=estimated_duration,
            status=ApplicationStatus.PENDING,
        )

        # Notify customer
        from notifications.services import NotificationService
        from notifications.models import NotificationType
        NotificationService.create_notification(
            user=task.customer,
            notification_type=NotificationType.SYSTEM,
            title="New Task Application",
            message=f"{professional.full_name} submitted a bid of ₹{proposed_price} for your task '{task.title}'.",
        )

        return application

    @staticmethod
    @transaction.atomic
    def withdraw_application(application, professional):
        if application.professional != professional and not professional.is_staff:
            raise ValidationError("You do not have permission to withdraw this application.")

        if application.status != ApplicationStatus.PENDING:
            raise ValidationError(f"Cannot withdraw application in '{application.get_status_display()}' status.")

        application.status = ApplicationStatus.WITHDRAWN
        application.save(update_fields=["status", "updated_at"])

        return application

    @staticmethod
    @transaction.atomic
    def select_applicant(task, application, customer):
        """
        Atomic Selection of Professional:
        1. Validates ownership & task is OPEN.
        2. Validates application is PENDING and belongs to task.
        3. Selected application -> ACCEPTED.
        4. All other pending applications for this task -> REJECTED.
        5. Task -> ASSIGNED with assigned_professional & accepted_application.
        6. Logs status history and dispatches notifications.
        """
        if task.customer != customer and not customer.is_staff:
            raise ValidationError("Only the customer who created the task can select an applicant.")

        if task.status != TaskStatus.OPEN:
            raise ValidationError(f"Cannot assign professional. Task is currently in '{task.get_status_display()}' status.")

        if application.task != task:
            raise ValidationError("This application does not belong to the specified task.")

        if application.status != ApplicationStatus.PENDING:
            raise ValidationError(f"Cannot accept application with status '{application.get_status_display()}'.")

        # 1. Accept selected bid
        application.status = ApplicationStatus.ACCEPTED
        application.save(update_fields=["status", "updated_at"])

        # 2. Reject all other pending bids for this task
        competing_apps = task.applications.filter(status=ApplicationStatus.PENDING).exclude(id=application.id)
        rejected_workers = list(competing_apps.values_list("professional", flat=True))
        competing_apps.update(status=ApplicationStatus.REJECTED)

        # 3. Update Task
        task.status = TaskStatus.ASSIGNED
        task.assigned_professional = application.professional
        task.accepted_application = application
        task.save(update_fields=["status", "assigned_professional", "accepted_application", "updated_at"])

        # 4. Log History
        TaskStatusHistory.objects.create(
            task=task,
            status=TaskStatus.ASSIGNED,
            changed_by=customer,
            note=f"Customer selected {application.professional.full_name} (Bid: ₹{application.proposed_price}).",
            source="customer",
        )

        # 5. Notifications
        from notifications.services import NotificationService
        from notifications.models import NotificationType
        from accounts.models import User

        # Notify Winner
        NotificationService.create_notification(
            user=application.professional,
            notification_type=NotificationType.SYSTEM,
            title="Application Accepted!",
            message=f"Congratulations! Your bid of ₹{application.proposed_price} for '{task.title}' was accepted by {customer.full_name}.",
        )

        # Notify other applicants
        for r_user_id in rejected_workers:
            r_user = User.objects.filter(id=r_user_id).first()
            if r_user:
                NotificationService.create_notification(
                    user=r_user,
                    notification_type=NotificationType.SYSTEM,
                    title="Task Assigned to Another Professional",
                    message=f"The customer has selected another professional for task '{task.title}'.",
                )

        return task


class SmartMatchingService:

    @staticmethod
    def get_matching_professionals(task, limit=6):
        """
        Calculates a deterministic multi-signal match score (0-100) for professionals against a given task.
        Signals:
        1. Category / Skill alignment (40 pts)
        2. Location / City proximity (25 pts)
        3. Rating & Trust score (20 pts)
        4. KYC Verification status (10 pts)
        5. Experience level (5 pts)
        """
        category = task.category
        category_skills = set(category.skills.values_list("id", flat=True))

        profiles = (
            ProfessionalProfile.objects.filter(availability_status=ProfessionalProfile.AvailabilityStatus.AVAILABLE)
            .select_related("user", "user__profile")
            .prefetch_related("skills", "languages", "services")
        )

        matches = []
        for profile in profiles:
            user = profile.user
            # Skip the task owner
            if user == task.customer:
                continue

            score = 0
            breakdown = []

            # 1. Skill & Category alignment
            pro_skill_ids = set(profile.skills.values_list("id", flat=True))
            if category_skills and (category_skills & pro_skill_ids):
                score += 40
                breakdown.append("Skill Match (+40)")
            elif any(category.slug in s.service.slug or s.service.category.slug in category.slug for s in profile.services.all()):
                score += 35
                breakdown.append("Service Expertise Match (+35)")
            else:
                score += 15
                breakdown.append("General Marketplace Capability (+15)")

            # 2. Location Proximity
            u_prof = getattr(user, "profile", None)
            pro_city = (u_prof.city if u_prof else "").lower()
            if pro_city and task.city.lower() in pro_city:
                score += 25
                breakdown.append(f"Same City: {task.city} (+25)")
            else:
                score += 10
                breakdown.append("Regional Service Radius (+10)")

            # 3. Rating & Trust
            avg_rating = float(profile.average_rating or 4.5)
            if avg_rating >= 4.8:
                score += 20
                breakdown.append(f"Top Rated: {avg_rating}★ (+20)")
            elif avg_rating >= 4.0:
                score += 15
                breakdown.append(f"High Rating: {avg_rating}★ (+15)")
            else:
                score += 8
                breakdown.append(f"Rating: {avg_rating}★ (+8)")

            # 4. KYC Verification
            if profile.is_verified:
                score += 10
                breakdown.append("KYC Verified Professional (+10)")

            # 5. Experience Level
            exp = profile.experience_years or 0
            if exp >= 5:
                score += 5
                breakdown.append(f"{exp}+ Years Experience (+5)")
            elif exp >= 2:
                score += 3
                breakdown.append(f"{exp} Years Experience (+3)")

            matches.append({
                "professional_id": user.id,
                "professional_name": user.full_name or user.email,
                "title": profile.professional_title,
                "hourly_rate": profile.hourly_rate,
                "average_rating": avg_rating,
                "reviews_count": profile.reviews_count,
                "experience_years": exp,
                "is_verified": profile.is_verified,
                "city": pro_city.title(),
                "match_score": min(score, 100),
                "match_signals": breakdown,
            })

        matches.sort(key=lambda m: m["match_score"], reverse=True)
        return matches[:limit]
