from django.urls import path
from .views import (
    HealthcareServiceListAPIView,
    HealthcareCategoryListAPIView,
    HealthcareProfessionalListPublicAPIView,
    HealthcareOrganizationListPublicAPIView,
    HealthcareOrganizationDetailAPIView,
    HealthcareOrganizationDashboardAPIView,
    HealthcareOrganizationStaffAPIView,
    PatientMedicalProfileAPIView,
    EmergencyContactListCreateAPIView,
    EmergencyContactDetailAPIView,
    HealthcareAppointmentBookAPIView,
    HealthcareAppointmentListAPIView,
    HealthcareAppointmentDetailAPIView,
    MedicalVisitNoteListCreateAPIView,
    PatientInstructionAcknowledgeAPIView,
    HealthcareProfessionalProfileAPIView,
)

urlpatterns = [
    # Public Healthcare Catalog
    path("services/", HealthcareServiceListAPIView.as_view(), name="healthcare_services_list"),
    path("categories/", HealthcareCategoryListAPIView.as_view(), name="healthcare_categories"),
    path("professionals/", HealthcareProfessionalListPublicAPIView.as_view(), name="healthcare_public_professionals"),
    path("organizations/", HealthcareOrganizationListPublicAPIView.as_view(), name="healthcare_public_organizations"),
    path("organizations/<str:slug_or_id>/", HealthcareOrganizationDetailAPIView.as_view(), name="healthcare_organization_detail"),

    # Organization Dashboard & Staff Management
    path("organization/dashboard/", HealthcareOrganizationDashboardAPIView.as_view(), name="healthcare_organization_dashboard"),
    path("organization/staff/", HealthcareOrganizationStaffAPIView.as_view(), name="healthcare_organization_staff"),

    # Patient Profile & Emergency Contacts
    path("profile/", PatientMedicalProfileAPIView.as_view(), name="healthcare_patient_profile"),
    path("emergency-contacts/", EmergencyContactListCreateAPIView.as_view(), name="healthcare_emergency_contacts_list_create"),
    path("emergency-contacts/<int:pk>/", EmergencyContactDetailAPIView.as_view(), name="healthcare_emergency_contacts_detail"),

    # Appointments & Clinical Notes
    path("appointments/book/", HealthcareAppointmentBookAPIView.as_view(), name="healthcare_appointment_book"),
    path("appointments/", HealthcareAppointmentListAPIView.as_view(), name="healthcare_appointment_list"),
    path("appointments/<str:booking_number>/", HealthcareAppointmentDetailAPIView.as_view(), name="healthcare_appointment_detail"),
    path("appointments/<str:booking_number>/notes/", MedicalVisitNoteListCreateAPIView.as_view(), name="healthcare_appointment_notes"),
    path("appointments/<str:booking_number>/instructions/<int:instruction_id>/ack/", PatientInstructionAcknowledgeAPIView.as_view(), name="healthcare_instruction_ack"),
    
    # Healthcare Professional Credentials
    path("professional/profile/", HealthcareProfessionalProfileAPIView.as_view(), name="healthcare_pro_profile"),
]
