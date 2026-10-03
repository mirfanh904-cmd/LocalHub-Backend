from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse, OpenApiParameter

from api.permissions import IsAdmin
from accounts.models import User, ProfessionalProfile
from bookings.models import (
    Booking,
    Complaint,
    ComplaintStatus,
    ReviewReport,
    ReportStatus,
)
from verification.models import (
    ProfessionalVerification,
    VerificationStatus,
)
from verification.services import VerificationService
from verification.expiry_service import DocumentExpiryService
from dashboard.selectors import AdminDashboardSelector
from bookings.services import BookingService, ComplaintService, ReviewReportService
from .serializers import (
    AdminUserSerializer,
    AdminVerificationListSerializer,
    AdminVerificationDetailSerializer,
    AdminVerificationActionSerializer,
    AdminComplaintListSerializer,
    AdminComplaintDetailSerializer,
    AdminComplaintActionSerializer,
    AdminReviewReportSerializer,
    AdminReviewReportActionSerializer,
)


class AdminDashboardAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="get_admin_dashboard_stats",
        summary="Retrieve Admin Dashboard Statistics",
        description="Returns system-wide aggregated metrics, active bookings, total revenue, verification queues, and dispute status.",
        responses={200: OpenApiResponse(description="System-wide metrics and dashboard statistics")},
        tags=["Admin - Dashboard"],
    )
    def get(self, request):
        stats = AdminDashboardSelector.get_statistics()
        return Response(stats, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_all_users",
        summary="List All Users",
        description="Returns all registered customer, professional, and staff users.",
        tags=["Admin - Users"],
    ),
    retrieve=extend_schema(
        operation_id="retrieve_user_by_admin",
        summary="Retrieve User",
        description="Returns account details of a specific user.",
        tags=["Admin - Users"],
    ),
    partial_update=extend_schema(
        operation_id="update_user_status_by_admin",
        summary="Update User Status / Role",
        description="Modifies user active status, staff permissions, or basic info.",
        tags=["Admin - Users"],
    ),
)
class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "patch"]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = ["created_at", "first_name"]


# ==========================================
# ADMIN - VERIFICATION WORKFLOW
# ==========================================

class AdminVerificationListAPIView(generics.ListAPIView):
    serializer_class = AdminVerificationListSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="list_verifications_admin",
        summary="List Professional Verifications",
        description="Returns all professional KYC verification dossiers with optional status filter (pending, under_review, approved, rejected, expired, suspended).",
        parameters=[
            OpenApiParameter("status", str, description="Filter by status (pending/under_review/approved/rejected/expired/suspended)"),
            OpenApiParameter("search", str, description="Search by professional name or email"),
        ],
        tags=["Admin - Verification"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = ProfessionalVerification.objects.select_related("professional", "professional__user").prefetch_related("documents")
        status_param = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        if status_param:
            qs = qs.filter(status=status_param)
        if search:
            qs = qs.filter(
                professional__user__first_name__icontains=search
            ) | qs.filter(
                professional__user__last_name__icontains=search
            ) | qs.filter(
                professional__user__email__icontains=search
            )
        return qs.order_by("-updated_at")


class AdminVerificationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AdminVerificationDetailSerializer
    permission_classes = [IsAdmin]
    queryset = (
        ProfessionalVerification.objects
        .select_related("professional", "professional__user", "reviewed_by")
        .prefetch_related("documents", "history_logs", "history_logs__performed_by")
    )

    @extend_schema(
        operation_id="retrieve_verification_dossier",
        summary="Retrieve Professional Verification Dossier",
        description="Returns full verification details, uploaded documents, reviewer notes, and immutable timeline history.",
        tags=["Admin - Verification"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminApproveVerificationAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="approve_professional_verification",
        summary="Approve Professional Verification",
        description="Approves the KYC verification dossier of a professional, marking their profile as verified.",
        request=AdminVerificationActionSerializer,
        responses={
            200: AdminVerificationDetailSerializer,
            400: OpenApiResponse(description="Invalid state transition"),
        },
        tags=["Admin - Verification"],
    )
    def post(self, request, pk):
        verification = get_object_or_404(ProfessionalVerification, id=pk)
        serializer = AdminVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verification = VerificationService.approve_verification(
                verification=verification,
                admin=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Professional verification approved successfully.",
                    "data": AdminVerificationDetailSerializer(verification).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminRejectVerificationAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="reject_professional_verification",
        summary="Reject Professional Verification",
        description="Rejects the KYC verification dossier of a professional with a mandatory reason.",
        request=AdminVerificationActionSerializer,
        responses={
            200: AdminVerificationDetailSerializer,
            400: OpenApiResponse(description="Missing rejection reason or invalid state"),
        },
        tags=["Admin - Verification"],
    )
    def post(self, request, pk):
        verification = get_object_or_404(ProfessionalVerification, id=pk)
        serializer = AdminVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get("reason")
        if not reason:
            return Response(
                {"success": False, "message": "Rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verification = VerificationService.reject_verification(
                verification=verification,
                admin=request.user,
                reason=reason,
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Professional verification rejected.",
                    "data": AdminVerificationDetailSerializer(verification).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminReviewVerificationAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="mark_verification_under_review",
        summary="Mark Verification Under Review",
        description="Transitions a pending verification dossier to under-review status.",
        request=AdminVerificationActionSerializer,
        responses={200: AdminVerificationDetailSerializer},
        tags=["Admin - Verification"],
    )
    def post(self, request, pk):
        verification = get_object_or_404(ProfessionalVerification, id=pk)
        serializer = AdminVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verification = VerificationService.mark_under_review(
                verification=verification,
                admin=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Verification marked as under review.",
                    "data": AdminVerificationDetailSerializer(verification).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminSuspendVerificationAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="suspend_professional_verification",
        summary="Suspend Professional Verification",
        description="Suspends an approved professional's verified badge and status due to safety concerns or disciplinary investigation.",
        request=AdminVerificationActionSerializer,
        responses={200: AdminVerificationDetailSerializer},
        tags=["Admin - Verification"],
    )
    def post(self, request, pk):
        verification = get_object_or_404(ProfessionalVerification, id=pk)
        serializer = AdminVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verification = VerificationService.suspend_verification(
                verification=verification,
                admin=request.user,
                reason=serializer.validated_data.get("reason", "Suspended by admin"),
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Professional verification suspended.",
                    "data": AdminVerificationDetailSerializer(verification).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminProcessExpiriesAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="process_verification_expiries",
        summary="Process KYC Document Expiries",
        description="Executes automated domain scan for expired KYC documents and updates associated verification dossiers to expired status.",
        request=None,
        responses={200: OpenApiResponse(description="Expiry scan summary")},
        tags=["Admin - Verification"],
    )
    def post(self, request):

        result = DocumentExpiryService.check_and_expire_documents(performed_by=request.user)
        return Response(
            {
                "success": True,
                "message": f"Processed KYC expiries: {result['expired_documents_count']} documents and {result['expired_verifications_count']} verifications marked as expired.",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )


# ==========================================
# ADMIN - COMPLAINTS WORKFLOW
# ==========================================

class AdminComplaintListAPIView(generics.ListAPIView):
    serializer_class = AdminComplaintListSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="list_complaints_admin",
        summary="List Trust & Safety Complaints",
        description="Returns all customer complaints and disputes across the platform with optional status filtering.",
        parameters=[
            OpenApiParameter("status", str, description="Filter by status (pending, under_investigation, resolved, rejected, closed)"),
            OpenApiParameter("category", str, description="Filter by category"),
        ],
        tags=["Admin - Complaints"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = Complaint.objects.select_related("customer", "professional")
        status_filter = self.request.query_params.get("status")
        category_filter = self.request.query_params.get("category")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)
        return qs.order_by("-created_at")


class AdminComplaintDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AdminComplaintDetailSerializer
    permission_classes = [IsAdmin]
    lookup_field = "complaint_number"
    queryset = Complaint.objects.select_related("customer", "professional", "booking", "resolved_by")

    @extend_schema(
        operation_id="retrieve_complaint_admin",
        summary="Retrieve Complaint Dossier",
        description="Returns full complaint details, booking context, resolution, and internal admin notes.",
        tags=["Admin - Complaints"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminInvestigateComplaintAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="investigate_complaint",
        summary="Mark Complaint Under Investigation",
        description="Moves a complaint to under-investigation status and records admin notes.",
        request=AdminComplaintActionSerializer,
        responses={200: AdminComplaintDetailSerializer},
        tags=["Admin - Complaints"],
    )
    def post(self, request, complaint_number):
        complaint = get_object_or_404(Complaint, complaint_number=complaint_number)
        serializer = AdminComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint = ComplaintService.investigate_complaint(
            complaint=complaint,
            admin_user=request.user,
            admin_notes=serializer.validated_data.get("admin_notes", ""),
        )
        return Response(
            {
                "success": True,
                "message": "Complaint moved to under investigation.",
                "data": AdminComplaintDetailSerializer(complaint).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminResolveComplaintAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="resolve_complaint",
        summary="Resolve Complaint",
        description="Marks a complaint as resolved with an official resolution outcome.",
        request=AdminComplaintActionSerializer,
        responses={200: AdminComplaintDetailSerializer},
        tags=["Admin - Complaints"],
    )
    def post(self, request, complaint_number):
        complaint = get_object_or_404(Complaint, complaint_number=complaint_number)
        serializer = AdminComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolution = serializer.validated_data.get("resolution")
        if not resolution:
            return Response(
                {"success": False, "message": "Resolution description is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            complaint = ComplaintService.resolve_complaint(
                complaint=complaint,
                admin_user=request.user,
                resolution=resolution,
                admin_notes=serializer.validated_data.get("admin_notes", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Complaint resolved successfully.",
                    "data": AdminComplaintDetailSerializer(complaint).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminRejectComplaintAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="reject_complaint",
        summary="Reject Complaint",
        description="Dismisses/rejects a complaint with a reason.",
        request=AdminComplaintActionSerializer,
        responses={200: AdminComplaintDetailSerializer},
        tags=["Admin - Complaints"],
    )
    def post(self, request, complaint_number):
        complaint = get_object_or_404(Complaint, complaint_number=complaint_number)
        serializer = AdminComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get("reason")
        if not reason:
            return Response(
                {"success": False, "message": "Reason for rejection is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            complaint = ComplaintService.reject_complaint(
                complaint=complaint,
                admin_user=request.user,
                reason=reason,
                admin_notes=serializer.validated_data.get("admin_notes", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Complaint rejected.",
                    "data": AdminComplaintDetailSerializer(complaint).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.message if hasattr(e, "message") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==========================================
# ADMIN - REVIEW REPORTS WORKFLOW
# ==========================================

class AdminReviewReportListAPIView(generics.ListAPIView):
    serializer_class = AdminReviewReportSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="list_review_reports_admin",
        summary="List Flagged Review Reports",
        description="Returns all customer reviews flagged by users for moderation.",
        tags=["Admin - Reviews"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return (
            ReviewReport.objects
            .select_related("review", "review__customer", "reporter")
            .order_by("-created_at")
        )


class AdminReviewReportActionAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="moderate_review_report",
        summary="Take Action on Review Report",
        description="Resolves or dismisses a review report with moderation notes.",
        request=AdminReviewReportActionSerializer,
        responses={200: AdminReviewReportSerializer},
        tags=["Admin - Reviews"],
    )
    def post(self, request, pk):
        report = get_object_or_404(ReviewReport, id=pk)
        serializer = AdminReviewReportActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("admin_notes", "")

        status_val = ReportStatus.RESOLVED if action == "resolved" else ReportStatus.DISMISSED
        report = ReviewReportService.moderate_report(
            report=report,
            admin_user=request.user,
            status=status_val,
            admin_notes=notes,
        )
        return Response(
            {
                "success": True,
                "message": f"Review report marked as {action}.",
                "data": AdminReviewReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )


# ==========================================
# ADMIN - BOOKING ASSIGNMENT WORKFLOW
# ==========================================

class AdminAssignBookingAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="assign_booking_worker_admin",
        summary="Assign Worker or Override Booking Status",
        description="Allows platform administrators to assign or reassign a professional worker to a booking or override booking status.",
        request=None,
        responses={200: OpenApiResponse(description="Booking assignment or status updated successfully")},
        tags=["Admin - Bookings"],
    )
    def post(self, request, booking_number):

        booking = get_object_or_404(Booking, booking_number=booking_number)
        worker_id = request.data.get("worker_id")
        new_status = request.data.get("status")

        if worker_id:
            worker_user = get_object_or_404(User, id=worker_id)
            BookingService.assign_worker(booking, worker_user, changed_by=request.user)

        if new_status:
            BookingService.change_status(
                booking=booking,
                status=new_status,
                changed_by=request.user,
                source="admin",
                note="Status overridden by admin API."
            )

        return Response(
            {"success": True, "message": "Booking assignment / status updated successfully."},
            status=status.HTTP_200_OK,
        )


# ==========================================
# ADMIN - HEALTHCARE MANAGEMENT WORKFLOW
# ==========================================

from healthcare.models import HealthcareOrganization, HealthcareProfessionalProfile
from django.utils import timezone
from .serializers import (
    AdminHealthcareOrganizationSerializer,
    AdminHealthcareProfessionalSerializer,
)


class AdminHealthcareOrganizationListAPIView(generics.ListAPIView):
    serializer_class = AdminHealthcareOrganizationSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="list_healthcare_organizations_admin",
        summary="List Healthcare Organizations (Admin)",
        description="Returns all healthcare organizations with verification filter.",
        tags=["Admin - Healthcare"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = HealthcareOrganization.objects.all().select_related("owner").order_by("-created_at")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(verification_status=status_param)
        return qs


class AdminHealthcareOrganizationApproveAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="approve_healthcare_organization_admin",
        summary="Approve Healthcare Organization",
        description="Approves a healthcare organization and marks it verified.",
        request=None,
        responses={200: AdminHealthcareOrganizationSerializer},
        tags=["Admin - Healthcare"],
    )
    def post(self, request, pk):
        org = get_object_or_404(HealthcareOrganization, id=pk)
        org.is_verified = True
        org.verification_status = "approved"
        org.verified_at = timezone.now()
        org.rejection_reason = ""
        org.save()
        return Response({
            "success": True,
            "message": f"Organization '{org.name}' has been approved.",
            "data": AdminHealthcareOrganizationSerializer(org).data,
        }, status=status.HTTP_200_OK)


class AdminHealthcareOrganizationRejectAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="reject_healthcare_organization_admin",
        summary="Reject Healthcare Organization",
        description="Rejects a healthcare organization with reason.",
        request=None,
        responses={200: AdminHealthcareOrganizationSerializer},
        tags=["Admin - Healthcare"],
    )
    def post(self, request, pk):
        org = get_object_or_404(HealthcareOrganization, id=pk)
        reason = request.data.get("reason", "Credentials did not satisfy compliance requirements.")
        org.is_verified = False
        org.verification_status = "rejected"
        org.rejection_reason = reason
        org.save()
        return Response({
            "success": True,
            "message": f"Organization '{org.name}' has been rejected.",
            "data": AdminHealthcareOrganizationSerializer(org).data,
        }, status=status.HTTP_200_OK)


class AdminHealthcareProfessionalListAPIView(generics.ListAPIView):
    serializer_class = AdminHealthcareProfessionalSerializer
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="list_healthcare_professionals_admin",
        summary="List Healthcare Professional Applications (Admin)",
        description="Returns all registered medical practitioners and credentialing status.",
        tags=["Admin - Healthcare"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = HealthcareProfessionalProfile.objects.all().select_related("professional").order_by("-created_at")
        verified_param = self.request.query_params.get("verified")
        if verified_param is not None:
            qs = qs.filter(is_license_verified=(verified_param.lower() == "true"))
        return qs


class AdminHealthcareProfessionalApproveAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="approve_healthcare_professional_admin",
        summary="Approve Healthcare Professional License",
        description="Approves a healthcare professional's clinical registration.",
        request=None,
        responses={200: AdminHealthcareProfessionalSerializer},
        tags=["Admin - Healthcare"],
    )
    def post(self, request, pk):
        pro = get_object_or_404(HealthcareProfessionalProfile, id=pk)
        pro.is_license_verified = True
        pro.verified_at = timezone.now()
        pro.save()

        # Also update verification record if present
        if hasattr(pro.professional, "professional_profile"):
            ver = getattr(pro.professional.professional_profile, "verification", None)
            if ver:
                ver.status = "approved"
                ver.reviewed_at = timezone.now()
                ver.reviewed_by = request.user
                ver.save()

        return Response({
            "success": True,
            "message": f"Healthcare professional '{pro.professional.full_name}' license approved.",
            "data": AdminHealthcareProfessionalSerializer(pro).data,
        }, status=status.HTTP_200_OK)


class AdminHealthcareProfessionalRejectAPIView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="reject_healthcare_professional_admin",
        summary="Reject Healthcare Professional License",
        description="Rejects a healthcare professional's clinical credentials.",
        request=None,
        responses={200: AdminHealthcareProfessionalSerializer},
        tags=["Admin - Healthcare"],
    )
    def post(self, request, pk):
        pro = get_object_or_404(HealthcareProfessionalProfile, id=pk)
        pro.is_license_verified = False
        pro.save()

        return Response({
            "success": True,
            "message": f"Healthcare professional '{pro.professional.full_name}' credentials rejected.",
            "data": AdminHealthcareProfessionalSerializer(pro).data,
        }, status=status.HTTP_200_OK)