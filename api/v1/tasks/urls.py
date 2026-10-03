from django.urls import path
from .views import (
    TaskCategoryListView,
    TaskListView,
    TaskDetailView,
    TaskPublishView,
    TaskCancelView,
    TaskApplicationsView,
    TaskApplicationWithdrawView,
    TaskApplicationSelectView,
    TaskStartView,
    TaskCompleteView,
    TaskMatchingProfessionalsView,
    CustomerMyTasksView,
    ProfessionalMyApplicationsView,
    ProfessionalAssignedTasksView,
)

urlpatterns = [
    # Task Categories
    path("categories/", TaskCategoryListView.as_view(), name="task-categories"),

    # Task Discovery & Management
    path("", TaskListView.as_view(), name="task-list"),
    path("my-tasks/", CustomerMyTasksView.as_view(), name="customer-my-tasks"),
    path("my-applications/", ProfessionalMyApplicationsView.as_view(), name="professional-my-applications"),
    path("my-assigned-jobs/", ProfessionalAssignedTasksView.as_view(), name="professional-assigned-jobs"),

    # Task Detail & Actions
    path("<uuid:id>/", TaskDetailView.as_view(), name="task-detail"),
    path("<uuid:id>/publish/", TaskPublishView.as_view(), name="task-publish"),
    path("<uuid:id>/cancel/", TaskCancelView.as_view(), name="task-cancel"),
    path("<uuid:id>/start/", TaskStartView.as_view(), name="task-start"),
    path("<uuid:id>/complete/", TaskCompleteView.as_view(), name="task-complete"),
    path("<uuid:id>/matching-professionals/", TaskMatchingProfessionalsView.as_view(), name="task-matching-pros"),

    # Applications & Bidding
    path("<uuid:id>/applications/", TaskApplicationsView.as_view(), name="task-applications"),
    path("applications/<uuid:id>/withdraw/", TaskApplicationWithdrawView.as_view(), name="task-application-withdraw"),
    path("applications/<uuid:id>/select/", TaskApplicationSelectView.as_view(), name="task-application-select"),
]
