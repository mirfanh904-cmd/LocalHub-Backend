from decimal import Decimal
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from services.models import Category, Service, ServiceGroup
from accounts.models import Address
from bookings.models import BookingStatus
from bookings.services import BookingService

from healthcare.models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
    AppointmentType,
    ClinicalSpecialty,
)
from healthcare.services import (
    PatientProfileService,
    EmergencyContactService,
    HealthcareAppointmentService,
    MedicalVisitNoteService,
    HealthcareProfessionalService,
)

User = get_user_model()


class HealthcareModelAndServiceTests(TestCase):

    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="patient@localhub.com",
            password="password123",
            first_name="John",
            last_name="Doe",
            role="CUSTOMER",
        )
        self.doctor_user = User.objects.create_user(
            email="doctor@localhub.com",
            password="password123",
            first_name="Dr. Sarah",
            last_name="Smith",
            role="PROFESSIONAL",
        )
        self.other_user = User.objects.create_user(
            email="other@localhub.com",
            password="password123",
            first_name="Other",
            last_name="User",
            role="CUSTOMER",
        )
        self.group = ServiceGroup.objects.create(name="Healthcare", slug="healthcare", theme_color="#0D9488")
        self.category = Category.objects.create(name="Doctor Visit", slug="doctor-visit", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="Doctor Home Visit", slug="doctor-home-visit", starting_price=Decimal("499.00"))
        self.address = Address.objects.create(
            user=self.patient_user,
            full_name="John Doe",
            phone="9876543210",
            house_name="12A",
            area="Indiranagar",
            city="Bangalore",
            state="Karnataka",
            country="India",
            postal_code="560038",
        )

    def test_patient_medical_profile_creation_and_update(self):
        profile = PatientProfileService.update_profile(self.patient_user, {
            "gender": "male",
            "date_of_birth": datetime.date(1990, 5, 15),
            "blood_group": "O+",
            "chronic_conditions": "Hypertension",
            "allergies": "Penicillin",
            "mobility_assistance": True,
        })
        self.assertEqual(profile.blood_group, "O+")
        self.assertEqual(profile.chronic_conditions, "Hypertension")
        self.assertTrue(profile.mobility_assistance)

        # Future date of birth should raise ValidationError
        with self.assertRaises(ValidationError):
            PatientProfileService.update_profile(self.patient_user, {
                "date_of_birth": datetime.date(2050, 1, 1),
            })

    def test_emergency_contact_workflow(self):
        c1 = EmergencyContactService.create_contact(self.patient_user, {
            "name": "Jane Doe",
            "relationship": "Spouse",
            "phone_number": "9876543211",
            "is_primary": True,
        })
        self.assertTrue(c1.is_primary)

        c2 = EmergencyContactService.create_contact(self.patient_user, {
            "name": "Bob Doe",
            "relationship": "Brother",
            "phone_number": "9876543212",
            "is_primary": True,
        })
        c1.refresh_from_db()
        self.assertFalse(c1.is_primary)
        self.assertTrue(c2.is_primary)

        # Delete c2, c1 becomes primary
        EmergencyContactService.delete_contact(self.patient_user, c2.id)
        c1.refresh_from_db()
        self.assertTrue(c1.is_primary)

    def test_healthcare_booking_and_instructions(self):
        appointment = HealthcareAppointmentService.book_healthcare_appointment(
            customer=self.patient_user,
            booking_payload={
                "service": self.service,
                "address": self.address,
                "worker": self.doctor_user,
                "booking_date": datetime.date.today() + datetime.timedelta(days=1),
                "start_time": datetime.time(10, 0),
                "end_time": datetime.time(11, 0),
                "subtotal": Decimal("499.00"),
                "total_amount": Decimal("499.00"),
            },
            healthcare_payload={
                "appointment_type": AppointmentType.DOCTOR_VISIT,
                "symptoms": "High fever and persistent cough",
                "accessibility_needs": "Elevator access available",
            },
        )
        self.assertEqual(appointment.booking.status, BookingStatus.PENDING)
        self.assertEqual(appointment.appointment_type, AppointmentType.DOCTOR_VISIT)
        self.assertEqual(appointment.symptoms, "High fever and persistent cough")

        # Instruction generated
        instructions = appointment.instructions.all()
        self.assertEqual(instructions.count(), 1)
        inst = instructions.first()
        self.assertFalse(inst.is_acknowledged)

        # Patient acknowledges instruction
        HealthcareAppointmentService.acknowledge_instruction(self.patient_user, appointment, inst.id)
        inst.refresh_from_db()
        self.assertTrue(inst.is_acknowledged)
        self.assertIsNotNone(inst.acknowledged_at)

    def test_clinical_visit_notes_and_vitals_validation(self):
        appointment = HealthcareAppointmentService.book_healthcare_appointment(
            customer=self.patient_user,
            booking_payload={
                "service": self.service,
                "address": self.address,
                "worker": self.doctor_user,
                "booking_date": datetime.date.today(),
                "start_time": datetime.time(10, 0),
                "end_time": datetime.time(11, 0),
                "subtotal": Decimal("499.00"),
                "total_amount": Decimal("499.00"),
            },
            healthcare_payload={
                "appointment_type": AppointmentType.DOCTOR_VISIT,
            },
        )

        # Non-assigned worker cannot author clinical notes
        with self.assertRaises(ValidationError):
            MedicalVisitNoteService.record_visit_note(
                appointment=appointment,
                author=self.other_user,
                validated_data={
                    "systolic_bp": 120,
                    "diastolic_bp": 80,
                    "clinical_observations": "Unassigned note",
                },
            )

        # Invalid vitals validation
        with self.assertRaises(ValidationError):
            MedicalVisitNoteService.record_visit_note(
                appointment=appointment,
                author=self.doctor_user,
                validated_data={
                    "systolic_bp": 80,
                    "diastolic_bp": 120, # Diastolic greater than systolic
                    "clinical_observations": "Invalid vitals",
                },
            )

        # Valid clinical note
        note = MedicalVisitNoteService.record_visit_note(
            appointment=appointment,
            author=self.doctor_user,
            validated_data={
                "systolic_bp": 122,
                "diastolic_bp": 82,
                "heart_rate_bpm": 74,
                "temperature_f": Decimal("98.6"),
                "oxygen_saturation": 99,
                "clinical_observations": "Lungs clear bilaterally. Vitals stable.",
                "care_recommendations": "Hydration and rest for 48 hours.",
            },
        )
        self.assertEqual(note.systolic_bp, 122)
        self.assertEqual(note.heart_rate_bpm, 74)
        self.assertEqual(note.author, self.doctor_user)


class HealthcareAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(email="api_patient@localhub.com", password="password123", first_name="Pat", last_name="User", role="CUSTOMER")
        self.doctor = User.objects.create_user(email="api_doc@localhub.com", password="password123", first_name="Doc", last_name="User", role="PROFESSIONAL")
        self.stranger = User.objects.create_user(email="api_stranger@localhub.com", password="password123", first_name="Stranger", last_name="User", role="CUSTOMER")
        
        self.group = ServiceGroup.objects.create(name="Healthcare Services", slug="healthcare-services", theme_color="#0D9488")
        self.category = Category.objects.create(name="Nursing Care", slug="nursing-care", service_group=self.group)
        self.service = Service.objects.create(category=self.category, name="Post-Op Nursing", slug="post-op-nursing", starting_price=Decimal("350.00"))
        self.address = Address.objects.create(user=self.patient, full_name="Pat", phone="123", house_name="1", area="A", city="C", state="S", country="In", postal_code="1")

    def test_healthcare_api_flow(self):
        # 1. Update patient profile
        self.client.force_authenticate(user=self.patient)
        p_res = self.client.put("/api/v1/healthcare/profile/", data={
            "blood_group": "AB+",
            "chronic_conditions": "None",
            "allergies": "None",
        }, format="json")
        self.assertEqual(p_res.status_code, 200)

        # 2. Add emergency contact
        e_res = self.client.post("/api/v1/healthcare/emergency-contacts/", data={
            "name": "Emergency Person",
            "relationship": "Parent",
            "phone_number": "9999999999",
            "is_primary": True,
        }, format="json")
        self.assertEqual(e_res.status_code, 201)
        contact_id = e_res.data["data"]["id"]

        # 3. Book appointment
        b_res = self.client.post("/api/v1/healthcare/appointments/book/", data={
            "service": self.service.id,
            "address": self.address.id,
            "worker": self.doctor.id,
            "booking_date": (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "subtotal": "350.00",
            "appointment_type": "nursing",
            "symptoms": "Wound dressing change",
            "emergency_contact_id": contact_id,
        }, format="json")
        self.assertEqual(b_res.status_code, 201)
        booking_num = b_res.data["data"]["booking_details"]["booking_number"]

        # 4. Stranger cannot view appointment detail
        self.client.force_authenticate(user=self.stranger)
        s_res = self.client.get(f"/api/v1/healthcare/appointments/{booking_num}/")
        self.assertEqual(s_res.status_code, 404)

        # 5. Doctor views appointment detail & adds clinical note
        self.client.force_authenticate(user=self.doctor)
        d_res = self.client.get(f"/api/v1/healthcare/appointments/{booking_num}/")
        self.assertEqual(d_res.status_code, 200)

        n_res = self.client.post(f"/api/v1/healthcare/appointments/{booking_num}/notes/", data={
            "systolic_bp": 118,
            "diastolic_bp": 78,
            "heart_rate_bpm": 72,
            "temperature_f": "98.4",
            "oxygen_saturation": 98,
            "clinical_observations": "Wound healing properly. Dressing changed aseptically.",
            "care_recommendations": "Keep area dry.",
        }, format="json")
        self.assertEqual(n_res.status_code, 201)
