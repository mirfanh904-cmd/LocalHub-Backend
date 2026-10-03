from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, financial_views

router = DefaultRouter()
router.register("users", views.AdminUserViewSet, basename="admin_users")

urlpatterns = [
    path("dashboard/", views.AdminDashboardAPIView.as_view(), name="admin_dashboard"),
    
    # Admin Verifications
    path("verifications/", views.AdminVerificationListAPIView.as_view(), name="admin_verification_list"),
    path("verifications/process-expiries/", views.AdminProcessExpiriesAPIView.as_view(), name="admin_process_expiries"),
    path("verifications/<int:pk>/", views.AdminVerificationDetailAPIView.as_view(), name="admin_verification_detail"),
    path("verifications/<int:pk>/approve/", views.AdminApproveVerificationAPIView.as_view(), name="admin_verification_approve"),
    path("verifications/<int:pk>/reject/", views.AdminRejectVerificationAPIView.as_view(), name="admin_verification_reject"),
    path("verifications/<int:pk>/review/", views.AdminReviewVerificationAPIView.as_view(), name="admin_verification_review"),
    path("verifications/<int:pk>/suspend/", views.AdminSuspendVerificationAPIView.as_view(), name="admin_verification_suspend"),

    # Admin Complaints
    path("complaints/", views.AdminComplaintListAPIView.as_view(), name="admin_complaint_list"),
    path("complaints/<str:complaint_number>/", views.AdminComplaintDetailAPIView.as_view(), name="admin_complaint_detail"),
    path("complaints/<str:complaint_number>/investigate/", views.AdminInvestigateComplaintAPIView.as_view(), name="admin_complaint_investigate"),
    path("complaints/<str:complaint_number>/resolve/", views.AdminResolveComplaintAPIView.as_view(), name="admin_complaint_resolve"),
    path("complaints/<str:complaint_number>/reject/", views.AdminRejectComplaintAPIView.as_view(), name="admin_complaint_reject"),

    # Admin Review Reports
    path("review-reports/", views.AdminReviewReportListAPIView.as_view(), name="admin_review_reports_list"),
    path("review-reports/<int:pk>/action/", views.AdminReviewReportActionAPIView.as_view(), name="admin_review_report_action"),

    # Admin Bookings
    path("bookings/<str:booking_number>/assign/", views.AdminAssignBookingAPIView.as_view(), name="admin_assign_booking"),
    
    # Admin Financial Ecosystem (Phase 7)
    path("financials/overview/", financial_views.AdminFinancialOverviewAPIView.as_view(), name="admin_financial_overview"),
    path("financials/payments/", financial_views.AdminPaymentsListAPIView.as_view(), name="admin_financial_payments"),
    path("financials/refunds/", financial_views.AdminRefundsListAPIView.as_view(), name="admin_financial_refunds"),
    path("financials/refunds/<uuid:pk>/action/", financial_views.AdminRefundActionAPIView.as_view(), name="admin_financial_refund_action"),
    path("financials/payouts/", financial_views.AdminPayoutsListAPIView.as_view(), name="admin_financial_payouts"),
    # Admin Healthcare Verifications & Organizations
    path("healthcare/organizations/", views.AdminHealthcareOrganizationListAPIView.as_view(), name="admin_healthcare_organizations"),
    path("healthcare/organizations/<uuid:pk>/approve/", views.AdminHealthcareOrganizationApproveAPIView.as_view(), name="admin_healthcare_org_approve"),
    path("healthcare/organizations/<uuid:pk>/reject/", views.AdminHealthcareOrganizationRejectAPIView.as_view(), name="admin_healthcare_org_reject"),
    path("healthcare/professionals/", views.AdminHealthcareProfessionalListAPIView.as_view(), name="admin_healthcare_professionals"),
    path("healthcare/professionals/<int:pk>/approve/", views.AdminHealthcareProfessionalApproveAPIView.as_view(), name="admin_healthcare_pro_approve"),
    path("healthcare/professionals/<int:pk>/reject/", views.AdminHealthcareProfessionalRejectAPIView.as_view(), name="admin_healthcare_pro_reject"),

    path("", include(router.urls)),
]