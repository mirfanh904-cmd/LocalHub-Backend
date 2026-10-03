from django.contrib import admin
from .models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
)


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


class PatientInstructionInline(admin.TabularInline):
    model = PatientInstruction
    extra = 0


class MedicalVisitNoteInline(admin.StackedInline):
    model = MedicalVisitNote
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PatientMedicalProfile)
class PatientMedicalProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "gender", "date_of_birth", "blood_group", "mobility_assistance", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "blood_group", "chronic_conditions"]
    list_filter = ["gender", "mobility_assistance", "blood_group"]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ["name", "patient", "relationship", "phone_number", "is_primary", "created_at"]
    search_fields = ["name", "patient__email", "phone_number"]
    list_filter = ["is_primary", "relationship"]


@admin.register(HealthcareProfessionalProfile)
class HealthcareProfessionalProfileAdmin(admin.ModelAdmin):
    list_display = ["professional", "clinical_specialty", "registration_number", "registration_council", "is_license_verified", "created_at"]
    search_fields = ["professional__email", "professional__first_name", "professional__last_name", "registration_number", "medical_degree"]
    list_filter = ["clinical_specialty", "is_license_verified"]


@admin.register(HealthcareAppointment)
class HealthcareAppointmentAdmin(admin.ModelAdmin):
    list_display = ["booking", "appointment_type", "is_emergency", "created_at"]
    search_fields = ["booking__booking_number", "booking__customer__email", "booking__worker__email", "symptoms"]
    list_filter = ["appointment_type", "is_emergency"]
    inlines = [PatientInstructionInline, MedicalVisitNoteInline]


@admin.register(MedicalVisitNote)
class MedicalVisitNoteAdmin(admin.ModelAdmin):
    list_display = ["appointment", "author", "systolic_bp", "diastolic_bp", "heart_rate_bpm", "temperature_f", "oxygen_saturation", "created_at"]
    search_fields = ["appointment__booking__booking_number", "author__email", "clinical_observations"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PatientInstruction)
class PatientInstructionAdmin(admin.ModelAdmin):
    list_display = ["title", "appointment", "requires_fasting", "is_acknowledged", "created_at"]
    search_fields = ["title", "appointment__booking__booking_number"]
    list_filter = ["requires_fasting", "is_acknowledged"]
