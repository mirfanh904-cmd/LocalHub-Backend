from django.db.models import Q
from .models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
)


class HealthcareSelector:

    @staticmethod
    def get_patient_profile(user):
        profile, _ = PatientMedicalProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def list_emergency_contacts(user):
        return EmergencyContact.objects.filter(patient=user).order_by("-is_primary", "-created_at")

    @staticmethod
    def get_healthcare_professional_profile(user):
        return HealthcareProfessionalProfile.objects.filter(professional=user).first()

    @staticmethod
    def list_verified_healthcare_professionals(specialty=None):
        qs = HealthcareProfessionalProfile.objects.filter(
            is_license_verified=True,
            professional__is_active=True,
        ).select_related("professional")
        if specialty:
            qs = qs.filter(clinical_specialty=specialty)
        return qs

    @staticmethod
    def list_appointments_for_user(user):
        if getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN":
            return HealthcareAppointment.objects.all().select_related("booking", "booking__customer", "booking__worker", "patient_profile", "emergency_contact")
        return HealthcareAppointment.objects.filter(
            Q(booking__customer=user) | Q(booking__worker=user)
        ).select_related("booking", "booking__customer", "booking__worker", "patient_profile", "emergency_contact")

    @staticmethod
    def get_appointment_by_booking_number(booking_number, user=None):
        qs = HealthcareAppointment.objects.select_related(
            "booking",
            "booking__customer",
            "booking__worker",
            "patient_profile",
            "emergency_contact",
        ).prefetch_related("instructions", "medical_notes", "medical_notes__author")
        
        if user:
            if not (getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN"):
                qs = qs.filter(Q(booking__customer=user) | Q(booking__worker=user))
        
        return qs.filter(booking__booking_number=booking_number).first()

    @staticmethod
    def get_clinical_notes_for_appointment(appointment):
        return MedicalVisitNote.objects.filter(appointment=appointment).select_related("author").order_by("-created_at")
