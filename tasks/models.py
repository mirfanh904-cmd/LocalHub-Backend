import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from common.models import BaseModel


class TaskCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=100, default="bi-grid")
    theme_color = models.CharField(max_length=20, default="#2563EB")
    display_order = models.PositiveIntegerField(default=0)
    skills = models.ManyToManyField(
        "accounts.Skill",
        blank=True,
        related_name="task_categories",
    )

    class Meta:
        db_table = "tasks_categories"
        ordering = ["display_order", "name"]
        verbose_name = "Task Category"
        verbose_name_plural = "Task Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TaskStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    OPEN = "open", "Open (Accepting Applications)"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class Task(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    task_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_tasks",
    )
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    title = models.CharField(
        max_length=200,
    )
    description = models.TextField()
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    house_name = models.CharField(
        max_length=200,
        blank=True,
    )
    area = models.CharField(
        max_length=200,
        blank=True,
    )
    city = models.CharField(
        max_length=100,
    )
    postal_code = models.CharField(
        max_length=10,
    )
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    status = models.CharField(
        max_length=30,
        choices=TaskStatus.choices,
        default=TaskStatus.OPEN,
        db_index=True,
    )
    assigned_professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    accepted_application = models.OneToOneField(
        "TaskApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_for_task",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    cancellation_reason = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "tasks_task"
        ordering = ["-created_at"]
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self):
        return f"{self.task_number} - {self.title} ({self.get_status_display()})"

    @property
    def applications_count(self):
        return self.applications.filter(status=ApplicationStatus.PENDING).count()

    @property
    def total_applications_count(self):
        return self.applications.count()


class TaskApplication(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_applications",
    )
    proposed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    proposal = models.TextField()
    estimated_duration = models.CharField(
        max_length=100,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        db_index=True,
    )
    applied_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "tasks_application"
        ordering = ["-applied_at"]
        verbose_name = "Task Application"
        verbose_name_plural = "Task Applications"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "professional"],
                name="unique_task_application_per_pro",
            )
        ]

    def __str__(self):
        return f"Bid by {self.professional.full_name} for {self.task.task_number}: ₹{self.proposed_price} ({self.get_status_display()})"


class TaskStatusHistory(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(
        max_length=30,
        choices=TaskStatus.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(
        blank=True,
    )
    source = models.CharField(
        max_length=20,
        choices=[
            ("customer", "Customer"),
            ("professional", "Professional"),
            ("admin", "Admin"),
            ("system", "System"),
        ],
        default="system",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "tasks_status_history"
        ordering = ["-created_at"]
        verbose_name = "Task Status History"
        verbose_name_plural = "Task Status Histories"

    def __str__(self):
        return f"{self.task.task_number} -> {self.status} at {self.created_at}"
