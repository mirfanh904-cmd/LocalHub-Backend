from django.db.models import Q
from .models import Task, TaskCategory, TaskApplication, TaskStatus, ApplicationStatus


def get_task_categories():
    return TaskCategory.objects.filter(is_active=True).order_by("display_order", "name")


def get_public_tasks(search=None, category_slug=None, city=None, min_budget=None, max_budget=None, ordering="-created_at"):
    qs = (
        Task.objects.filter(status=TaskStatus.OPEN, is_active=True)
        .select_related("customer", "category", "address")
        .prefetch_related("applications")
    )

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(city__icontains=search)
            | Q(category__name__icontains=search)
        )

    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    if city:
        qs = qs.filter(city__iexact=city)

    if min_budget:
        qs = qs.filter(budget__gte=min_budget)

    if max_budget:
        qs = qs.filter(budget__lte=max_budget)

    allowed_orderings = ["created_at", "-created_at", "budget", "-budget", "preferred_date", "-preferred_date"]
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("-created_at")

    return qs


def get_customer_tasks(user, status=None, ordering="-created_at"):
    qs = (
        Task.objects.filter(customer=user, is_active=True)
        .select_related("category", "assigned_professional", "accepted_application", "address")
        .prefetch_related("applications__professional")
    )
    if status:
        qs = qs.filter(status=status)
    return qs.order_by(ordering)


def get_professional_applications(user, status=None):
    qs = (
        TaskApplication.objects.filter(professional=user)
        .select_related("task", "task__category", "task__customer")
        .order_by("-applied_at")
    )
    if status:
        qs = qs.filter(status=status)
    return qs


def get_professional_assigned_tasks(user, status=None):
    qs = (
        Task.objects.filter(assigned_professional=user, is_active=True)
        .select_related("customer", "category", "address", "accepted_application")
        .order_by("-updated_at")
    )
    if status:
        qs = qs.filter(status=status)
    return qs
