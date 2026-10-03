from django.conf import settings
from django.db import models
from django.utils.text import slugify
from common.models import BaseModel
from verification.models import VerificationStatus, DocumentStatus


class GenderChoices(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class ClinicalSpecialty(models.TextChoices):
    GENERAL_PHYSICIAN = "general_physician", "General Physician"
    HOME_NURSE = "home_nurse", "Home Nurse"
    PHYSIOTHERAPIST = "physiotherapist", "Physiotherapist"
    ELDERLY_CAREGIVER = "elderly_caregiver", "Elderly Caregiver"
    LAB_TECHNICIAN = "lab_technician", "Lab Technician"
    NUTRITIONIST = "nutritionist", "Nutrition Consultant"


class AppointmentType(models.TextChoices):
    NURSING = "nursing", "Home Nursing"
    DOCTOR_VISIT = "doctor_visit", "Doctor Home Visit"
    PHYSIOTHERAPY = "physiotherapy", "Physiotherapy Session"
    ELDER_CARE = "elder_care", "Elderly Caregiver Assistance"
    LAB_TEST = "lab_test", "Lab Sample Collection"


class OrganizationType(models.TextChoices):
    HOSPITAL = "hospital", "Hospital"
    CLINIC = "clinic", "Clinic"
    DIAGNOSTIC_CENTRE = "diagnostic_centre", "Diagnostic Centre / Laboratory"
    HEALTHCARE_AGENCY = "healthcare_agency", "Healthcare Agency"
    OTHER = "other", "Other Organization"


class OrganizationRole(models.TextChoices):
    OWNER = "owner", "Owner / Administrator"
    DOCTOR = "doctor", "Doctor"
    NURSE = "nurse", "Nurse"
    PHYSIOTHERAPIST = "physiotherapist", "Physiotherapist"
    STAFF = "staff", "Clinical / Administrative Staff"


class HealthcareOrganization(BaseModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    organization_type = models.CharField(
        max_length=50,
        choices=OrganizationType.choices,
        default=OrganizationType.CLINIC,
    )
    registration_number = models.CharField(max_length=100, unique=True)
    license_number = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    services = models.ManyToManyField(
        "services.Service",
        blank=True,
        related_name="healthcare_organizations",
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    reviews_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Healthcare Organization"
        verbose_name_plural = "Healthcare Organizations"

    def __str__(self):
        return f"{self.name} ({self.get_organization_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while HealthcareOrganization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class OrganizationMembership(BaseModel):
    organization = models.ForeignKey(
        HealthcareOrganization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    professional_profile = models.ForeignKey(
        "accounts.ProfessionalProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=50,
        choices=OrganizationRole.choices,
        default=OrganizationRole.STAFF,
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-joined_at"]
        unique_together = ("organization", "user")
        verbose_name = "Organization Membership"
        verbose_name_plural = "Organization Memberships"

    def __str__(self):
        return f"{self.user.full_name or self.user.email} - {self.organization.name} ({self.get_role_display()})"


class OrganizationVerificationDocument(BaseModel):
    organization = models.ForeignKey(
        HealthcareOrganization,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=100)
    document_number = models.CharField(max_length=100, blank=True)
    document_file = models.FileField(upload_to="organizations/documents/")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_org_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Organization Verification Document"
        verbose_name_plural = "Organization Verification Documents"

    def __str__(self):
        return f"{self.organization.name} - {self.document_type} ({self.get_status_display()})"


class PatientMedicalProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=GenderChoices.choices,
        default=GenderChoices.PREFER_NOT_TO_SAY,
    )
    blood_group = models.CharField(max_length=10, blank=True)
    chronic_conditions = models.TextField(
        blank=True,
        help_text="Known pre-existing conditions (e.g., Hypertension, Diabetes, Asthma)",
    )
    allergies = models.TextField(
        blank=True,
        help_text="Known drug, food, or environmental allergies",
    )
    mobility_assistance = models.BooleanField(
        default=False,
        help_text="Whether patient requires wheelchair or physical mobility assistance",
    )
    special_accommodations = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Patient Medical Profile"
        verbose_name_plural = "Patient Medical Profiles"

    def __str__(self):
        return f"Patient Profile: {self.user.full_name or self.user.email}"


class EmergencyContact(BaseModel):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.phone_number}"


class HealthcareProfessionalProfile(BaseModel):
    professional = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="healthcare_profile",
    )
    registration_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="State or National Medical / Nursing Council Registration Number",
    )
    registration_council = models.CharField(
        max_length=200,
        help_text="Name of Medical / Nursing / Physiotherapy Council",
    )
    medical_degree = models.CharField(
        max_length=150,
        help_text="Highest relevant medical degree (e.g. MBBS, MD, B.Sc Nursing, BPT)",
    )
    clinical_specialty = models.CharField(
        max_length=50,
        choices=ClinicalSpecialty.choices,
        default=ClinicalSpecialty.GENERAL_PHYSICIAN,
    )
    years_of_clinical_exp = models.PositiveIntegerField(default=0)
    is_license_verified = models.BooleanField(
        default=False,
        help_text="Verified by LocalHub administrative and credentialing team",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Healthcare Professional Profile"
        verbose_name_plural = "Healthcare Professional Profiles"

    def __str__(self):
        return f"{self.professional.full_name} ({self.get_clinical_specialty_display()}) - Reg: {self.registration_number}"


class HealthcareAppointment(BaseModel):
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="healthcare_details",
    )
    organization = models.ForeignKey(
        HealthcareOrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    patient_profile = models.ForeignKey(
        PatientMedicalProfile,
        on_delete=models.PROTECT,
        related_name="appointments",
        null=True,
        blank=True,
    )
    emergency_contact = models.ForeignKey(
        EmergencyContact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    appointment_type = models.CharField(
        max_length=50,
        choices=AppointmentType.choices,
        default=AppointmentType.DOCTOR_VISIT,
    )
    symptoms = models.TextField(
        blank=True,
        help_text="Current symptoms or reason for in-home consultation",
    )
    accessibility_needs = models.TextField(
        blank=True,
        help_text="Staircase assistance, oxygen support, bedside assistance, etc.",
    )
    pre_visit_instructions = models.TextField(
        blank=True,
        help_text="Preparation notes before practitioner arrival (e.g., fasting, reports ready)",
    )
    is_emergency = models.BooleanField(
        default=False,
        help_text="Flagged for high-priority clinical response",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Healthcare Appointment"
        verbose_name_plural = "Healthcare Appointments"

    def __str__(self):
        return f"Healthcare Detail for Booking {self.booking.booking_number} ({self.get_appointment_type_display()})"


class PatientInstruction(BaseModel):
    appointment = models.ForeignKey(
        HealthcareAppointment,
        on_delete=models.CASCADE,
        related_name="instructions",
    )
    title = models.CharField(max_length=200)
    instruction_text = models.TextField()
    requires_fasting = models.BooleanField(default=False)
    fasting_hours = models.PositiveIntegerField(null=True, blank=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Patient Pre-Visit Instruction"
        verbose_name_plural = "Patient Pre-Visit Instructions"

    def __str__(self):
        return f"{self.title} (Booking {self.appointment.booking.booking_number})"


class MedicalVisitNote(BaseModel):
    appointment = models.ForeignKey(
        HealthcareAppointment,
        on_delete=models.CASCADE,
        related_name="medical_notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_medical_notes",
    )
    systolic_bp = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Systolic Blood Pressure (mmHg)",
    )
    diastolic_bp = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Diastolic Blood Pressure (mmHg)",
    )
    heart_rate_bpm = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Heart Rate (BPM)",
    )
    temperature_f = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Body Temperature (°F)",
    )
    oxygen_saturation = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="SpO2 Blood Oxygen Percentage (%)",
    )
    clinical_observations = models.TextField(
        help_text="Clinical findings, physical examination notes, wound condition, etc.",
    )
    care_recommendations = models.TextField(
        blank=True,
        help_text="Post-visit patient care recommendations, rest schedule, or follow-up advice",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Medical Visit Note"
        verbose_name_plural = "Medical Visit Notes"

    def __str__(self):
        return f"Visit Note for {self.appointment.booking.booking_number} by {self.author.full_name}"
