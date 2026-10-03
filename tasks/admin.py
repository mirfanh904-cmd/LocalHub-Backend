from django.contrib import admin
from .models import TaskCategory, Task, TaskApplication, TaskStatusHistory


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "display_order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description"]
    list_filter = ["is_active"]


class TaskApplicationInline(admin.TabularInline):
    model = TaskApplication
    extra = 0
    readonly_fields = ["applied_at", "updated_at"]


class TaskStatusHistoryInline(admin.TabularInline):
    model = TaskStatusHistory
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "task_number",
        "title",
        "customer",
        "category",
        "budget",
        "city",
        "status",
        "assigned_professional",
        "created_at",
    ]
    list_filter = ["status", "category", "city", "created_at"]
    search_fields = ["task_number", "title", "description", "customer__email", "customer__first_name"]
    readonly_fields = ["task_number", "created_at", "updated_at"]
    inlines = [TaskApplicationInline, TaskStatusHistoryInline]


@admin.register(TaskApplication)
class TaskApplicationAdmin(admin.ModelAdmin):
    list_display = ["task", "professional", "proposed_price", "status", "applied_at"]
    list_filter = ["status", "applied_at"]
    search_fields = ["task__task_number", "professional__email", "professional__first_name", "proposal"]


@admin.register(TaskStatusHistory)
class TaskStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["task", "status", "changed_by", "source", "created_at"]
    list_filter = ["status", "source", "created_at"]
    search_fields = ["task__task_number", "note"]
