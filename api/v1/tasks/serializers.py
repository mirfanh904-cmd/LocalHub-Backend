from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from accounts.models import User, Address
from tasks.models import Task, TaskCategory, TaskApplication, TaskStatusHistory, TaskStatus, ApplicationStatus


class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon_class",
            "theme_color",
            "display_order",
            "is_active",
        ]


class TaskStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True, default="System")

    class Meta:
        model = TaskStatusHistory
        fields = [
            "id",
            "status",
            "changed_by_name",
            "note",
            "source",
            "created_at",
        ]


class ApplicantProfessionalMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    professional_title = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()
    experience_years = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "professional_title",
            "average_rating",
            "reviews_count",
            "is_verified",
            "hourly_rate",
            "experience_years",
        ]

    @extend_schema_field(serializers.CharField())
    def get_professional_title(self, obj):
        p = getattr(obj, "professional_profile", None)
        return p.professional_title if p else "Professional"

    @extend_schema_field(serializers.FloatField())
    def get_average_rating(self, obj):
        p = getattr(obj, "professional_profile", None)
        return float(p.average_rating) if p else 4.9

    @extend_schema_field(serializers.IntegerField())
    def get_reviews_count(self, obj):
        p = getattr(obj, "professional_profile", None)
        return p.reviews_count if p else 0

    @extend_schema_field(serializers.BooleanField())
    def get_is_verified(self, obj):
        p = getattr(obj, "professional_profile", None)
        return p.is_verified if p else False

    @extend_schema_field(serializers.CharField())
    def get_hourly_rate(self, obj):
        p = getattr(obj, "professional_profile", None)
        return str(p.hourly_rate) if p and p.hourly_rate else "299.00"

    @extend_schema_field(serializers.IntegerField())
    def get_experience_years(self, obj):
        p = getattr(obj, "professional_profile", None)
        return p.experience_years if p else 0


class TaskApplicationSerializer(serializers.ModelSerializer):
    professional = ApplicantProfessionalMiniSerializer(read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)
    task_number = serializers.CharField(source="task.task_number", read_only=True)
    task_budget = serializers.DecimalField(source="task.budget", max_digits=10, decimal_places=2, read_only=True)
    task_city = serializers.CharField(source="task.city", read_only=True)
    task_status = serializers.CharField(source="task.status", read_only=True)

    class Meta:
        model = TaskApplication
        fields = [
            "id",
            "task",
            "task_title",
            "task_number",
            "task_budget",
            "task_city",
            "task_status",
            "professional",
            "proposed_price",
            "proposal",
            "estimated_duration",
            "status",
            "applied_at",
            "updated_at",
        ]
        read_only_fields = ["id", "task", "professional", "status", "applied_at", "updated_at"]


class TaskApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskApplication
        fields = [
            "proposed_price",
            "proposal",
            "estimated_duration",
        ]

    def validate_proposed_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Proposed price must be greater than zero.")
        return value


class CustomerMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name"]


class TaskListSerializer(serializers.ModelSerializer):
    category = TaskCategorySerializer(read_only=True)
    customer = CustomerMiniSerializer(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    total_applications_count = serializers.IntegerField(read_only=True)
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "task_number",
            "title",
            "description",
            "budget",
            "city",
            "postal_code",
            "preferred_date",
            "preferred_time",
            "status",
            "category",
            "customer",
            "applications_count",
            "total_applications_count",
            "has_applied",
            "created_at",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_has_applied(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            return obj.applications.filter(professional=request.user).exists()
        return False


class TaskDetailSerializer(serializers.ModelSerializer):
    category = TaskCategorySerializer(read_only=True)
    customer = CustomerMiniSerializer(read_only=True)
    assigned_professional = ApplicantProfessionalMiniSerializer(read_only=True)
    accepted_application = TaskApplicationSerializer(read_only=True)
    applications = serializers.SerializerMethodField()
    status_history = TaskStatusHistorySerializer(many=True, read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    total_applications_count = serializers.IntegerField(read_only=True)
    user_application = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "task_number",
            "title",
            "description",
            "budget",
            "address",
            "house_name",
            "area",
            "city",
            "postal_code",
            "preferred_date",
            "preferred_time",
            "status",
            "category",
            "customer",
            "assigned_professional",
            "accepted_application",
            "applications",
            "status_history",
            "applications_count",
            "total_applications_count",
            "user_application",
            "completed_at",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(TaskApplicationSerializer(many=True))
    def get_applications(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return []

        # Customer who created the task (or admin) sees all applications
        if obj.customer == request.user or request.user.is_staff:
            return TaskApplicationSerializer(obj.applications.all(), many=True, context=self.context).data

        # Professional sees only their own application if any
        user_app = obj.applications.filter(professional=request.user).first()
        if user_app:
            return [TaskApplicationSerializer(user_app, context=self.context).data]
        return []

    @extend_schema_field(TaskApplicationSerializer(allow_null=True))
    def get_user_application(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            app = obj.applications.filter(professional=request.user).first()
            if app:
                return TaskApplicationSerializer(app, context=self.context).data
        return None


class TaskCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TaskCategory.objects.filter(is_active=True),
        source="category",
        write_only=True,
    )
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source="address",
        required=False,
        allow_null=True,
        write_only=True,
    )
    is_draft = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = Task
        fields = [
            "category_id",
            "title",
            "description",
            "budget",
            "address_id",
            "house_name",
            "area",
            "city",
            "postal_code",
            "preferred_date",
            "preferred_time",
            "is_draft",
        ]

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than zero.")
        return value


class TaskCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SmartMatchSerializer(serializers.Serializer):
    professional_id = serializers.UUIDField()
    professional_name = serializers.CharField()
    title = serializers.CharField()
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    average_rating = serializers.FloatField()
    reviews_count = serializers.IntegerField()
    experience_years = serializers.IntegerField()
    is_verified = serializers.BooleanField()
    city = serializers.CharField()
    match_score = serializers.IntegerField()
    match_signals = serializers.ListField(child=serializers.CharField())
