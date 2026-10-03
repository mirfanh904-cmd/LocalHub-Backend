from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from bookings.services import BookingService
from notifications.services import NotificationService
from notifications.models import NotificationType

from .models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
    AppointmentType,
)
from .validators import HealthcareValidator


class PatientProfileService:

    @staticmethod
    @transaction.atomic
    def update_profile(user, validated_data):
        dob = validated_data.get("date_of_birth")
        if dob:
            HealthcareValidator.validate_date_of_birth(dob)

        profile, _ = PatientMedicalProfile.objects.get_or_create(user=user)
        for key, val in validated_data.items():
            setattr(profile, key, val)
        profile.save()
        return profile


class EmergencyContactService:

    @staticmethod
    @transaction.atomic
    def create_contact(user, validated_data):
        is_primary = validated_data.get("is_primary", False)
        if is_primary:
            EmergencyContact.objects.filter(patient=user, is_primary=True).update(is_primary=False)
        
        # If this is the user's first contact, make it primary automatically
        if not EmergencyContact.objects.filter(patient=user).exists():
            is_primary = True
            validated_data["is_primary"] = True

        contact = EmergencyContact.objects.create(patient=user, **validated_data)
        return contact

    @staticmethod
    @transaction.atomic
    def delete_contact(user, contact_id):
        contact = EmergencyContact.objects.filter(patient=user, id=contact_id).first()
        if not contact:
            raise ValidationError("Emergency contact not found.")
        
        was_primary = contact.is_primary
        contact.delete()

        if was_primary:
            next_contact = EmergencyContact.objects.filter(patient=user).first()
            if next_contact:
                next_contact.is_primary = True
                next_contact.save(update_fields=["is_primary"])
        return True


class HealthcareAppointmentService:

    @staticmethod
    @transaction.atomic
    def book_healthcare_appointment(customer, booking_payload, healthcare_payload):
        """
        Creates a standard Booking via Phase 5 BookingService, then attaches
        the HealthcareAppointment and default clinical instructions.
        """
        booking_payload["customer"] = customer
        booking = BookingService.create(booking_payload)

        # Ensure patient profile exists
        patient_profile, _ = PatientMedicalProfile.objects.get_or_create(user=customer)

        emergency_contact = None
        contact_id = healthcare_payload.get("emergency_contact_id")
        if contact_id:
            emergency_contact = EmergencyContact.objects.filter(patient=customer, id=contact_id).first()
        if not emergency_contact:
            emergency_contact = EmergencyContact.objects.filter(patient=customer, is_primary=True).first()

        appointment_type = healthcare_payload.get("appointment_type", AppointmentType.DOCTOR_VISIT)
        symptoms = healthcare_payload.get("symptoms", "")
        accessibility_needs = healthcare_payload.get("accessibility_needs", "")
        is_emergency = healthcare_payload.get("is_emergency", False)

        appointment = HealthcareAppointment.objects.create(
            booking=booking,
            patient_profile=patient_profile,
            emergency_contact=emergency_contact,
            appointment_type=appointment_type,
            symptoms=symptoms,
            accessibility_needs=accessibility_needs,
            is_emergency=is_emergency,
        )

        # Generate standard pre-visit patient instructions based on appointment type
        HealthcareAppointmentService._generate_pre_visit_instructions(appointment)

        # Notification
        NotificationService.create_notification(
            user=customer,
            notification_type=NotificationType.BOOKING,
            title="Healthcare Appointment Booked",
            message=f"Your {appointment.get_appointment_type_display()} appointment ({booking.booking_number}) is booked.",
            booking=booking,
        )

        return appointment

    @staticmethod
    def _generate_pre_visit_instructions(appointment):
        app_type = appointment.appointment_type
        
        if app_type == AppointmentType.LAB_TEST:
            PatientInstruction.objects.create(
                appointment=appointment,
                title="10-12 Hour Overnight Fasting Required",
                instruction_text="Please do not consume food or caloric beverages for 10-12 hours prior to sample collection. Plain water is permitted.",
                requires_fasting=True,
                fasting_hours=12,
            )
        elif app_type == AppointmentType.DOCTOR_VISIT:
            PatientInstruction.objects.create(
                appointment=appointment,
                title="Prepare Previous Medical Records",
                instruction_text="Please have any recent prescriptions, lab reports, and current medication lists ready for the physician's review.",
                requires_fasting=False,
            )
        elif app_type == AppointmentType.PHYSIOTHERAPY:
            PatientInstruction.objects.create(
                appointment=appointment,
                title="Comfortable Attire & Open Area Setup",
                instruction_text="Wear loose athletic or comfortable clothing. Ensure a clear, well-ventilated space of at least 6x6 feet for exercises.",
                requires_fasting=False,
            )
        elif app_type == AppointmentType.NURSING:
            PatientInstruction.objects.create(
                appointment=appointment,
                title="Clean Surface & Prescribed Medication Ready",
                instruction_text="Keep current doctor's prescription, dressing materials, and prescribed injectable/infusion medications easily accessible.",
                requires_fasting=False,
            )

    @staticmethod
    @transaction.atomic
    def acknowledge_instruction(patient, appointment, instruction_id):
        instruction = PatientInstruction.objects.filter(appointment=appointment, id=instruction_id).first()
        if not instruction:
            raise ValidationError("Instruction not found.")
        if appointment.booking.customer != patient:
            raise ValidationError("You are not authorized to acknowledge this instruction.")
        
        instruction.is_acknowledged = True
        instruction.acknowledged_at = timezone.now()
        instruction.save(update_fields=["is_acknowledged", "acknowledged_at", "updated_at"])
        return instruction


class MedicalVisitNoteService:

    @staticmethod
    @transaction.atomic
    def record_visit_note(appointment, author, validated_data):
        # Must be assigned worker or admin
        is_worker = appointment.booking.worker == author
        is_admin = getattr(author, "is_staff", False) or getattr(author, "role", "") == "ADMIN"
        if not (is_worker or is_admin):
            raise ValidationError("Only the assigned healthcare professional can submit clinical visit notes.")

        HealthcareValidator.validate_vitals(
            systolic_bp=validated_data.get("systolic_bp"),
            diastolic_bp=validated_data.get("diastolic_bp"),
            heart_rate_bpm=validated_data.get("heart_rate_bpm"),
            temperature_f=validated_data.get("temperature_f"),
            oxygen_saturation=validated_data.get("oxygen_saturation"),
        )

        note = MedicalVisitNote.objects.create(
            appointment=appointment,
            author=author,
            **validated_data
        )

        NotificationService.create_notification(
            user=appointment.booking.customer,
            notification_type=NotificationType.BOOKING,
            title="Clinical Visit Summary Available",
            message=f"Clinical observation notes have been added for appointment {appointment.booking.booking_number}.",
            booking=appointment.booking,
        )

        return note


class HealthcareProfessionalService:

    @staticmethod
    @transaction.atomic
    def update_credentials(user, validated_data):
        reg_num = validated_data.get("registration_number")
        if reg_num:
            HealthcareValidator.validate_registration_number(reg_num)

        profile, _ = HealthcareProfessionalProfile.objects.get_or_create(professional=user)
        for key, val in validated_data.items():
            setattr(profile, key, val)
        profile.save()
        return profile
