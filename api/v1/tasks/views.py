from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from tasks.models import Task, TaskCategory, TaskApplication, TaskStatus
from tasks.selectors import (
    get_task_categories,
    get_public_tasks,
    get_customer_tasks,
    get_professional_applications,
    get_professional_assigned_tasks,
)
from tasks.services import TaskService, TaskApplicationService, SmartMatchingService
from tasks.permissions import (
    IsTaskCustomerOrReadOnly,
    IsProfessionalUser,
    IsAssignedProfessional,
    IsApplicationOwnerOrCustomer,
)
from .serializers import (
    TaskCategorySerializer,
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    TaskApplicationSerializer,
    TaskApplicationCreateSerializer,
    TaskCancelSerializer,
    SmartMatchSerializer,
)


@extend_schema(tags=["Task Marketplace"])
class TaskCategoryListView(generics.ListAPIView):
    """
    Public listing of active task categories.
    """
    permission_classes = [AllowAny]
    serializer_class = TaskCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return get_task_categories()


@extend_schema(
    tags=["Task Marketplace"],
    parameters=[
        OpenApiParameter("search", OpenApiTypes.STR, description="Keyword search in title, description, or city"),
        OpenApiParameter("category", OpenApiTypes.STR, description="Category slug filter"),
        OpenApiParameter("city", OpenApiTypes.STR, description="City location filter"),
        OpenApiParameter("min_budget", OpenApiTypes.NUMBER, description="Minimum budget filter"),
        OpenApiParameter("max_budget", OpenApiTypes.NUMBER, description="Maximum budget filter"),
        OpenApiParameter("ordering", OpenApiTypes.STR, description="Ordering: created_at, -created_at, budget, -budget, preferred_date, -preferred_date"),
    ],
)
class TaskListView(generics.ListCreateAPIView):
    """
    GET: Public discovery of open marketplace tasks.
    POST: Authenticated customer creates a new custom task.
    """
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TaskCreateSerializer
        return TaskListSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search")
        category_slug = self.request.query_params.get("category")
        city = self.request.query_params.get("city")
        min_budget = self.request.query_params.get("min_budget")
        max_budget = self.request.query_params.get("max_budget")
        ordering = self.request.query_params.get("ordering", "-created_at")

        return get_public_tasks(
            search=search,
            category_slug=category_slug,
            city=city,
            min_budget=min_budget,
            max_budget=max_budget,
            ordering=ordering,
        )

    def create(self, request, *args, **kwargs):
        serializer = TaskCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            task = TaskService.create_task(
                customer=request.user,
                category=data["category"],
                title=data["title"],
                description=data["description"],
                budget=data["budget"],
                preferred_date=data["preferred_date"],
                preferred_time=data["preferred_time"],
                city=data.get("city", ""),
                postal_code=data.get("postal_code", ""),
                address=data.get("address"),
                house_name=data.get("house_name", ""),
                area=data.get("area", ""),
                is_draft=data.get("is_draft", False),
            )
            out_serializer = TaskDetailSerializer(task, context={"request": request})
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"])
class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Public detailed task view.
    PUT/PATCH: Customer updates own draft/open task.
    DELETE: Customer cancels/deletes draft task.
    """
    lookup_field = "id"
    queryset = Task.objects.filter(is_active=True).select_related("category", "customer", "assigned_professional", "accepted_application", "address")

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsTaskCustomerOrReadOnly()]

    def get_serializer_class(self):
        return TaskDetailSerializer

    def perform_destroy(self, instance):
        if instance.status != TaskStatus.DRAFT:
            raise ValidationError("Only draft tasks can be permanently deleted. Use the cancel endpoint for active tasks.")
        instance.delete()


@extend_schema(tags=["Task Marketplace"], request=None, responses=TaskDetailSerializer)
class TaskPublishView(views.APIView):
    """
    POST: Publish a draft task to OPEN status.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        task = get_object_or_404(Task, id=id, is_active=True)
        try:
            published_task = TaskService.publish_draft_task(task, request.user)
            return Response(TaskDetailSerializer(published_task, context={"request": request}).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"], request=TaskCancelSerializer, responses=TaskDetailSerializer)
class TaskCancelView(views.APIView):
    """
    POST: Cancel an open or assigned task.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        task = get_object_or_404(Task, id=id, is_active=True)
        serializer = TaskCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        try:
            cancelled_task = TaskService.cancel_task(task, request.user, reason=reason)
            return Response(TaskDetailSerializer(cancelled_task, context={"request": request}).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"])
class TaskApplicationsView(generics.ListCreateAPIView):
    """
    GET: List applications for a specific task (Customer or Applicant).
    POST: Professional submits an application / bid for the task.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TaskApplicationCreateSerializer
        return TaskApplicationSerializer

    def get_queryset(self):
        task_id = self.kwargs.get("id")
        task = get_object_or_404(Task, id=task_id, is_active=True)

        if task.customer == self.request.user or self.request.user.is_staff:
            return task.applications.all()
        return task.applications.filter(professional=self.request.user)

    def create(self, request, id, *args, **kwargs):
        task = get_object_or_404(Task, id=id, is_active=True)
        serializer = TaskApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            application = TaskApplicationService.apply_to_task(
                task=task,
                professional=request.user,
                proposed_price=data["proposed_price"],
                proposal=data["proposal"],
                estimated_duration=data.get("estimated_duration", ""),
            )
            out_serializer = TaskApplicationSerializer(application, context={"request": request})
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"], request=None, responses=TaskApplicationSerializer)
class TaskApplicationWithdrawView(views.APIView):
    """
    POST: Professional withdraws a pending application.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        application = get_object_or_404(TaskApplication, id=id)
        try:
            withdrawn = TaskApplicationService.withdraw_application(application, request.user)
            return Response(TaskApplicationSerializer(withdrawn, context={"request": request}).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"], request=None, responses=TaskDetailSerializer)
class TaskApplicationSelectView(views.APIView):
    """
    POST: Customer accepts an application and assigns the task.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        application = get_object_or_404(TaskApplication.objects.select_related("task", "professional"), id=id)
        try:
            task = TaskApplicationService.select_applicant(
                task=application.task,
                application=application,
                customer=request.user,
            )
            return Response(TaskDetailSerializer(task, context={"request": request}).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"], request=None, responses=TaskDetailSerializer)
class TaskStartView(views.APIView):
    """
    POST: Assigned professional transitions task to IN_PROGRESS.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        task = get_object_or_404(Task, id=id, is_active=True)
        try:
            started_task = TaskService.start_task(task, request.user)
            return Response(TaskDetailSerializer(started_task, context={"request": request}).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"], request=None, responses=TaskDetailSerializer)
class TaskCompleteView(views.APIView):
    """
    POST: Assigned professional marks task as COMPLETED.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        task = get_object_or_404(Task, id=id, is_active=True)
        try:
            completed_task = TaskService.complete_task(task, request.user)
            return Response(TaskDetailSerializer(completed_task, context={"request": request}).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Task Marketplace"], responses=SmartMatchSerializer(many=True))
class TaskMatchingProfessionalsView(views.APIView):
    """
    GET: Compute smart matching signals and return top matched verified professionals for a task.
    """
    permission_classes = [AllowAny]

    def get(self, request, id):
        task = get_object_or_404(Task, id=id, is_active=True)
        matches = SmartMatchingService.get_matching_professionals(task, limit=6)
        serializer = SmartMatchSerializer(matches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Task Marketplace"],
    parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, description="Task status filter: draft, open, assigned, in_progress, completed, cancelled"),
    ],
)
class CustomerMyTasksView(generics.ListAPIView):
    """
    GET: Authenticated customer lists all their posted tasks.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskListSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        return get_customer_tasks(self.request.user, status=status_param)


@extend_schema(
    tags=["Task Marketplace"],
    parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, description="Application status filter: pending, accepted, rejected, withdrawn"),
    ],
)
class ProfessionalMyApplicationsView(generics.ListAPIView):
    """
    GET: Authenticated professional lists their submitted bids and applications.
    """
    permission_classes = [IsAuthenticated, IsProfessionalUser]
    serializer_class = TaskApplicationSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        return get_professional_applications(self.request.user, status=status_param)


@extend_schema(tags=["Task Marketplace"])
class ProfessionalAssignedTasksView(generics.ListAPIView):
    """
    GET: Authenticated professional lists tasks assigned to them.
    """
    permission_classes = [IsAuthenticated, IsProfessionalUser]
    serializer_class = TaskListSerializer

    def get_queryset(self):
        status_param = self.request.query_params.get("status")
        return get_professional_assigned_tasks(self.request.user, status=status_param)
