import os
import uuid
from decimal import Decimal
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Avg, Count
from django.utils import timezone
from django.utils.text import slugify

# Accounts Models
from accounts.models import (
    User,
    UserProfile,
    Address,
    Skill,
    Language,
    ProfessionalProfile,
    ProfessionalService,
    FavouriteService,
    FavouriteProfessional,
)

# Services Models
from services.models import (
    ServiceGroup,
    Category,
    Service,
    ServicePackage,
    ServicePackageInclude,
    ServiceRequirement,
    ServiceFAQ,
)
from services.choices import RequirementFieldType

from django.contrib.auth.hashers import make_password

# Bookings Models
from bookings.models import (
    Booking,
    BookingStatus,
    PaymentStatus,
    BookingStatusHistory,
    BookingOTP,
    BookingRescheduleRequest,
    RescheduleStatus,
    Review,
    ReviewReply,
    ReviewReport,
    ReportReason,
    ReportStatus,
    Complaint,
    ComplaintCategory,
    ComplaintStatus,
    ComplaintPriority,
)

# Verification Models
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationStatus,
    DocumentType,
    DocumentStatus,
    VerificationHistoryLog,
)

# Notifications Models
from notifications.models import Notification, NotificationType

# Tasks Models (Phase 4)
from tasks.models import (
    Task,
    TaskCategory,
    TaskApplication,
    TaskStatusHistory,
    TaskStatus,
    ApplicationStatus,
)

# Healthcare Models (Phase 6 & Healthcare Ecosystem)
from healthcare.models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
    ClinicalSpecialty,
    AppointmentType,
    GenderChoices,
    HealthcareOrganization,
    OrganizationMembership,
    OrganizationVerificationDocument,
    OrganizationType,
    OrganizationRole,
)

# Payments Models (Phase 7)
from payments.models import (
    Wallet,
    WalletTransaction,
    PromoCode,
    PromoDiscountType,
    Payment,
    PaymentMethod,
    PaymentStatus as FinancialPaymentStatus,
    EscrowHold,
    EscrowStatus,
    CommissionRecord,
    ProfessionalPayout,
    PayoutStatus,
    PayoutMethod,
    RefundRequest,
    RefundStatus,
    RefundMethod,
    Invoice,
    InvoiceStatus,
    TransactionType,
)


class Command(BaseCommand):
    help = "Seeds the LocalHub database with realistic, high-quality development data."

    DEV_PASSWORD = os.environ.get("LOCALHUB_DEV_PASSWORD", "LocalHub@123")

    # Master Seed Identifiers for Idempotent Cleanup and Lookup
    SEED_ADMIN_EMAIL = "admin@localhub.com"
    SEED_CUSTOMER_EMAILS = [
        "customer@localhub.com",
        "sarah.customer@localhub.com",
        "arjun.customer@localhub.com",
    ]
    SEED_WORKER_EMAILS = [
        "rahul.electrician@localhub.com",
        "ameen.plumber@localhub.com",
        "jithin.actech@localhub.com",
        "nisha.beauty@localhub.com",
        "vikram.painter@localhub.com",
        "dr.kavita.doctor@localhub.com",
        "sister.mary.nurse@localhub.com",
        "rohit.physio@localhub.com",
    ]
    ALL_SEED_EMAILS = [SEED_ADMIN_EMAIL] + SEED_CUSTOMER_EMAILS + SEED_WORKER_EMAILS

    SEED_GROUP_SLUGS = [
        "home-cleaning",
        "plumbing",
        "electrical",
        "ac-appliance",
        "painting-maintenance",
        "beauty-wellness",
        "healthcare-wellness",
        # Legacy initial scratch groups
        "home-services",
        "personal-services",
        "automotive",
        "test-group",
    ]

    SEED_BOOKING_NUMBERS = [f"BK-2026-{1001 + i}" for i in range(10)]
    SEED_COMPLAINT_NUMBERS = [f"CMP-2026-00{1 + i}" for i in range(3)]
    SEED_TASK_NUMBERS = [f"TSK-2026-{1001 + i}" for i in range(10)]
    SEED_TASK_CATEGORY_SLUGS = [
        "home-repairs",
        "furniture-assembly",
        "electrical-wiring",
        "painting-decor",
        "moving-lifting",
        "outdoor-yard",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Safely removes seed-managed records before reseeding.",
        )

    def handle(self, *args, **options):
        clean_mode = options.get("clean", False)

        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("  LOCALHUB DEVELOPMENT SEED DATA SYSTEM"))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        if clean_mode:
            self.stdout.write(self.style.WARNING("Running in --clean mode: Removing existing seed-managed records..."))
            self._clean_seed_data()
            self.stdout.write(self.style.SUCCESS("[OK] Seed data cleaned successfully."))

        with transaction.atomic():
            stats = self._seed_all()

        self._print_summary(stats)

    def _clean_seed_data(self):
        """
        Safely removes ONLY seed-managed development records.
        Preserves Django system tables, migrations, and developer accounts not in ALL_SEED_EMAILS.
        """
        with transaction.atomic():
            # Payments & Financial Ecosystem (Phase 7)
            ProfessionalPayout.objects.filter(professional__email__in=self.ALL_SEED_EMAILS).delete()
            RefundRequest.objects.filter(customer__email__in=self.ALL_SEED_EMAILS).delete()
            CommissionRecord.objects.filter(models.Q(professional__email__in=self.ALL_SEED_EMAILS) | models.Q(payment__customer__email__in=self.ALL_SEED_EMAILS)).delete()
            EscrowHold.objects.filter(models.Q(professional__email__in=self.ALL_SEED_EMAILS) | models.Q(payment__customer__email__in=self.ALL_SEED_EMAILS)).delete()
            Invoice.objects.filter(customer__email__in=self.ALL_SEED_EMAILS).delete()
            Payment.objects.filter(customer__email__in=self.ALL_SEED_EMAILS).delete()
            PromoCode.objects.filter(code__in=["WELCOME50", "LOCAL100", "FESTIVE20"]).delete()
            WalletTransaction.objects.filter(wallet__user__email__in=self.ALL_SEED_EMAILS).delete()
            Wallet.objects.filter(user__email__in=self.ALL_SEED_EMAILS).delete()

            # Healthcare (Phase 6 & Organizations)
            OrganizationVerificationDocument.objects.all().delete()
            OrganizationMembership.objects.all().delete()
            MedicalVisitNote.objects.all().delete()
            PatientInstruction.objects.all().delete()
            HealthcareAppointment.objects.all().delete()
            HealthcareOrganization.objects.all().delete()
            EmergencyContact.objects.filter(patient__email__in=self.ALL_SEED_EMAILS).delete()
            PatientMedicalProfile.objects.filter(user__email__in=self.ALL_SEED_EMAILS).delete()
            HealthcareProfessionalProfile.objects.filter(professional__email__in=self.ALL_SEED_EMAILS).delete()

            # 0. Tasks (Phase 4)
            seed_tasks = Task.objects.filter(
                models.Q(task_number__in=self.SEED_TASK_NUMBERS)
                | models.Q(customer__email__in=self.ALL_SEED_EMAILS)
            )
            TaskStatusHistory.objects.filter(task__in=seed_tasks).delete()
            TaskApplication.objects.filter(models.Q(task__in=seed_tasks) | models.Q(professional__email__in=self.ALL_SEED_EMAILS)).delete()
            seed_tasks.delete()
            TaskCategory.objects.filter(slug__in=self.SEED_TASK_CATEGORY_SLUGS).delete()

            seed_groups = ServiceGroup.objects.filter(slug__in=self.SEED_GROUP_SLUGS)
            seed_categories = Category.objects.filter(service_group__in=seed_groups)
            seed_services = Service.objects.filter(category__in=seed_categories)
            seed_workers = User.objects.filter(email__in=self.SEED_WORKER_EMAILS)
            seed_profiles = ProfessionalProfile.objects.filter(user__in=seed_workers)
            seed_addresses = Address.objects.filter(user__email__in=self.ALL_SEED_EMAILS)

            # 1. Target all bookings related to seed users or seed services or seed addresses
            target_bookings = Booking.objects.filter(
                models.Q(booking_number__in=self.SEED_BOOKING_NUMBERS)
                | models.Q(customer__email__in=self.ALL_SEED_EMAILS)
                | models.Q(service__in=seed_services)
                | models.Q(address__in=seed_addresses)
            )

            # 2. Complaints & Notifications
            Complaint.objects.filter(complaint_number__in=self.SEED_COMPLAINT_NUMBERS).delete()
            Complaint.objects.filter(customer__email__in=self.ALL_SEED_EMAILS).delete()
            Complaint.objects.filter(booking__in=target_bookings).delete()
            Notification.objects.filter(user__email__in=self.ALL_SEED_EMAILS).delete()

            # 3. Reviews, Replies, Reports
            target_reviews = Review.objects.filter(booking__in=target_bookings)
            ReviewReport.objects.filter(review__in=target_reviews).delete()
            ReviewReply.objects.filter(review__in=target_reviews).delete()
            target_reviews.delete()

            # 4. Bookings, OTP, Reschedule, and Status History
            BookingOTP.objects.filter(booking__in=target_bookings).delete()
            BookingRescheduleRequest.objects.filter(booking__in=target_bookings).delete()
            BookingStatusHistory.objects.filter(booking__in=target_bookings).delete()
            target_bookings.delete()

            # 5. Favourites
            FavouriteService.objects.filter(user__email__in=self.ALL_SEED_EMAILS).delete()
            FavouriteProfessional.objects.filter(user__email__in=self.ALL_SEED_EMAILS).delete()

            # 6. Verification & Documents & History
            seed_verifications = ProfessionalVerification.objects.filter(professional__in=seed_profiles)
            VerificationHistoryLog.objects.filter(verification__in=seed_verifications).delete()
            ProfessionalVerificationDocument.objects.filter(verification__in=seed_verifications).delete()
            seed_verifications.delete()

            # 7. Professional Services
            ProfessionalService.objects.filter(professional__in=seed_profiles).delete()

            # 8. Addresses & User Profiles & Users
            seed_addresses.delete()
            UserProfile.objects.filter(user__email__in=self.ALL_SEED_EMAILS).delete()
            User.objects.filter(email__in=self.ALL_SEED_EMAILS).delete()

            # 9. Service Taxonomy
            seed_packages = ServicePackage.objects.filter(service__in=seed_services)
            ServicePackageInclude.objects.filter(package__in=seed_packages).delete()
            ServiceRequirement.objects.filter(service__in=seed_services).delete()
            ServiceFAQ.objects.filter(service__in=seed_services).delete()
            seed_packages.delete()
            seed_services.delete()
            seed_categories.delete()
            seed_groups.delete()

            # 10. Master Skills & Languages
            skill_slugs = [
                "electrical-repair", "switch-socket-repair", "plumbing", "pipe-fitting",
                "drain-cleaning", "deep-cleaning", "ac-maintenance", "ac-installation",
                "interior-painting", "appliance-repair", "beauty-services", "home-sanitization",
                "general-medicine", "clinical-nursing", "physiotherapy", "elder-care", "phlebotomy",
            ]
            Skill.objects.filter(slug__in=skill_slugs).delete()

    def _seed_all(self):
        stats = {
            "skills": 0,
            "languages": 0,
            "service_groups": 0,
            "categories": 0,
            "services": 0,
            "packages": 0,
            "package_includes": 0,
            "requirements": 0,
            "faqs": 0,
            "customers": 0,
            "professionals": 0,
            "professional_services": 0,
            "addresses": 0,
            "verifications": 0,
            "verification_documents": 0,
            "verification_history": 0,
            "bookings": 0,
            "booking_history": 0,
            "booking_otps": 0,
            "booking_reschedule_requests": 0,
            "reviews": 0,
            "review_replies": 0,
            "review_reports": 0,
            "complaints": 0,
            "notifications": 0,
            "favourites": 0,
            "task_categories": 0,
            "tasks": 0,
            "task_applications": 0,
            "task_status_history": 0,
            "patient_profiles": 0,
            "emergency_contacts": 0,
            "healthcare_pro_profiles": 0,
            "healthcare_organizations": 0,
            "organization_memberships": 0,
            "organization_documents": 0,
            "healthcare_appointments": 0,
            "patient_instructions": 0,
            "medical_visit_notes": 0,
            "wallets": 0,
            "wallet_transactions": 0,
            "promo_codes": 0,
            "payments": 0,
            "invoices": 0,
            "escrow_holds": 0,
            "commission_records": 0,
            "payouts": 0,
            "refund_requests": 0,
        }

        # --------------------------------------------------
        # STEP 1: SYSTEM MASTER DATA (Skills & Languages)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Skills and Languages...")
        skills_data = [
            ("Electrical Repair", "electrical-repair"),
            ("Switch & Socket Repair", "switch-socket-repair"),
            ("Plumbing", "plumbing"),
            ("Pipe Fitting", "pipe-fitting"),
            ("Drain Cleaning", "drain-cleaning"),
            ("Deep Cleaning", "deep-cleaning"),
            ("AC Maintenance", "ac-maintenance"),
            ("AC Installation", "ac-installation"),
            ("Interior Painting", "interior-painting"),
            ("Appliance Repair", "appliance-repair"),
            ("Beauty Services", "beauty-services"),
            ("Home Sanitization", "home-sanitization"),
            ("General Medicine", "general-medicine"),
            ("Clinical Nursing", "clinical-nursing"),
            ("Physiotherapy & Rehab", "physiotherapy"),
            ("Elder Caregiving", "elder-care"),
            ("Phlebotomy & Lab Sampling", "phlebotomy"),
        ]
        skills_dict = {}
        for name, slug in skills_data:
            skill = Skill.objects.filter(slug=slug).first() or Skill.objects.filter(name__iexact=name).first()
            if skill:
                skill.name = name
                skill.slug = slug
                skill.is_active = True
                skill.save()
            else:
                skill = Skill.objects.create(name=name, slug=slug, is_active=True)
            skills_dict[slug] = skill
            stats["skills"] += 1

        languages_data = [
            ("Malayalam", "ml"),
            ("English", "en"),
            ("Hindi", "hi"),
            ("Tamil", "ta"),
        ]
        languages_dict = {}
        for name, code in languages_data:
            lang = Language.objects.filter(code=code).first() or Language.objects.filter(name__iexact=name).first()
            if lang:
                lang.name = name
                lang.code = code
                lang.is_active = True
                lang.save()
            else:
                lang = Language.objects.create(name=name, code=code, is_active=True)
            languages_dict[code] = lang
            languages_dict[name.lower()] = lang
            stats["languages"] += 1

        # --------------------------------------------------
        # STEP 2: SERVICE TAXONOMY (Groups & Categories)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Service Taxonomy...")
        groups_data = [
            {
                "name": "Home Cleaning",
                "slug": "home-cleaning",
                "short_description": "Comprehensive residential cleaning and sanitization.",
                "description": "Professional deep cleaning, sanitization, and specialized cleaning services tailored for modern homes.",
                "icon_class": "bi-stars",
                "theme_color": "#2563EB",
                "display_order": 1,
                "is_featured": True,
                "seo_title": "Best Home Cleaning Services | LocalHub",
                "seo_description": "Book trusted home and deep cleaning professionals near you.",
            },
            {
                "name": "Plumbing Services",
                "slug": "plumbing",
                "short_description": "Leakage repairs, pipe installations, and unclogging.",
                "description": "Expert plumbers for prompt leak repairs, bathroom fittings, tap replacements, and drainage solutions.",
                "icon_class": "bi-droplet-half",
                "theme_color": "#06B6D4",
                "display_order": 2,
                "is_featured": True,
                "seo_title": "Certified Plumbers on Demand | LocalHub",
                "seo_description": "Fast and reliable plumbing services for leaks and installations.",
            },
            {
                "name": "Electrical Repairs",
                "slug": "electrical",
                "short_description": "Wiring, appliance setups, switchboards, and fan repairs.",
                "description": "Certified electricians for residential wiring, switch installations, short circuits, and fixture setups.",
                "icon_class": "bi-lightning-charge",
                "theme_color": "#F59E0B",
                "display_order": 3,
                "is_featured": True,
                "seo_title": "Licensed Electricians Near You | LocalHub",
                "seo_description": "Safe, verified electrical installation and repairs.",
            },
            {
                "name": "AC & Appliance Repair",
                "slug": "ac-appliance",
                "short_description": "Air conditioner servicing, maintenance, and gas refills.",
                "description": "Keep your home cool with preventive AC maintenance, deep foam jet servicing, and setup.",
                "icon_class": "bi-snow",
                "theme_color": "#8B5CF6",
                "display_order": 4,
                "is_featured": True,
                "seo_title": "AC Repair & General Service | LocalHub",
                "seo_description": "Expert technicians for AC repair, gas filling, and servicing.",
            },
            {
                "name": "Painting & Maintenance",
                "slug": "painting-maintenance",
                "short_description": "Interior painting, waterproofing, and touch-ups.",
                "description": "Transform your spaces with expert wall painting, waterproof coatings, and seasonal maintenance.",
                "icon_class": "bi-brush",
                "theme_color": "#10B981",
                "display_order": 5,
                "is_featured": False,
                "seo_title": "Home Painting & Wall Care | LocalHub",
                "seo_description": "Experienced home painters for interior and exterior renovation.",
            },
            {
                "name": "Beauty & Wellness",
                "slug": "beauty-wellness",
                "short_description": "Salon at home, grooming, and personalized styling.",
                "description": "Certified beauticians and stylists delivering hygienic salon and grooming services at your doorstep.",
                "icon_class": "bi-scissors",
                "theme_color": "#EC4899",
                "display_order": 6,
                "is_featured": False,
                "seo_title": "Salon & Grooming at Home | LocalHub",
                "seo_description": "Relax with doorstep beauty, grooming, and spa services.",
            },
            {
                "name": "Healthcare & Clinical Care",
                "slug": "healthcare-wellness",
                "short_description": "In-home doctor visits, nursing, physiotherapy, and lab tests.",
                "description": "Licensed physicians, critical care nurses, and physiotherapists delivering clinical and assisted care in the comfort of your home.",
                "icon_class": "bi-heart-pulse",
                "theme_color": "#0D9488",
                "display_order": 7,
                "is_featured": True,
                "seo_title": "In-Home Healthcare & Nursing Services | LocalHub",
                "seo_description": "Book certified doctors, home nurses, and physiotherapists near you.",
            },
        ]
        groups_dict = {}
        for g in groups_data:
            slug = g.pop("slug")
            group, _ = ServiceGroup.objects.update_or_create(
                slug=slug,
                defaults=g,
            )
            groups_dict[slug] = group
            stats["service_groups"] += 1

        categories_data = [
            # Home Cleaning
            {
                "group": "home-cleaning",
                "name": "Full Home Cleaning",
                "slug": "full-home-cleaning",
                "short_description": "Complete deep cleaning for apartments and villas.",
                "bootstrap_icon": "bi-house-heart",
                "theme_color": "#2563EB",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "group": "home-cleaning",
                "name": "Kitchen & Bathroom",
                "slug": "kitchen-bathroom-cleaning",
                "short_description": "Intensive grease removal and bathroom descaling.",
                "bootstrap_icon": "bi-droplet",
                "theme_color": "#0284C7",
                "display_order": 2,
                "is_featured": True,
            },
            # Plumbing
            {
                "group": "plumbing",
                "name": "Plumbing Repair",
                "slug": "plumbing-repair",
                "short_description": "Tap leaks, valves, and water line fixtures.",
                "bootstrap_icon": "bi-tools",
                "theme_color": "#06B6D4",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "group": "plumbing",
                "name": "Drainage & Pipes",
                "slug": "drainage-pipes",
                "short_description": "Clog removal, sewer line repairs, and inspection.",
                "bootstrap_icon": "bi-water",
                "theme_color": "#0891B2",
                "display_order": 2,
                "is_featured": False,
            },
            # Electrical
            {
                "group": "electrical",
                "name": "Electrical Repair",
                "slug": "electrical-repair-cat",
                "short_description": "Sockets, switchboards, tripping breakers, and fuses.",
                "bootstrap_icon": "bi-lightning",
                "theme_color": "#F59E0B",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "group": "electrical",
                "name": "Wiring & Installation",
                "slug": "wiring-installation",
                "short_description": "Fan setup, chandelier mounting, and inverter wiring.",
                "bootstrap_icon": "bi-plug",
                "theme_color": "#D97706",
                "display_order": 2,
                "is_featured": False,
            },
            # AC & Appliance
            {
                "group": "ac-appliance",
                "name": "AC General Service",
                "slug": "ac-general-service-cat",
                "short_description": "Filter cleaning, cooling check, and gas top-up.",
                "bootstrap_icon": "bi-snow2",
                "theme_color": "#8B5CF6",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "group": "ac-appliance",
                "name": "AC Installation & Repair",
                "slug": "ac-install-repair-cat",
                "short_description": "Split and window AC mounting and compressor diagnostics.",
                "bootstrap_icon": "bi-wrench",
                "theme_color": "#7C3AED",
                "display_order": 2,
                "is_featured": False,
            },
            # Painting
            {
                "group": "painting-maintenance",
                "name": "Interior Painting",
                "slug": "interior-painting-cat",
                "short_description": "Room repainting, wall texture, and waterproofing.",
                "bootstrap_icon": "bi-paint-bucket",
                "theme_color": "#10B981",
                "display_order": 1,
                "is_featured": True,
            },
            # Beauty
            {
                "group": "beauty-wellness",
                "name": "Salon at Home",
                "slug": "salon-at-home",
                "short_description": "Haircut, styling, facial, and mani-pedi.",
                "bootstrap_icon": "bi-scissors",
                "theme_color": "#EC4899",
                "display_order": 1,
                "is_featured": True,
            },
            # Healthcare & Wellness
            {
                "group": "healthcare-wellness",
                "name": "Doctor In-Home Visit",
                "slug": "doctor-home-visit",
                "short_description": "General physician in-home consultation and vitals checkup.",
                "bootstrap_icon": "bi-person-badge",
                "theme_color": "#0D9488",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "group": "healthcare-wellness",
                "name": "Home Nursing Care",
                "slug": "home-nursing-care",
                "short_description": "Post-surgical dressing, IV infusion, and vital monitoring.",
                "bootstrap_icon": "bi-heart-pulse",
                "theme_color": "#0D9488",
                "display_order": 2,
                "is_featured": True,
            },
            {
                "group": "healthcare-wellness",
                "name": "Physiotherapy & Rehab",
                "slug": "physiotherapy-rehab",
                "short_description": "Mobility recovery, orthopedic therapy, and pain management.",
                "bootstrap_icon": "bi-activity",
                "theme_color": "#0D9488",
                "display_order": 3,
                "is_featured": True,
            },
            {
                "group": "healthcare-wellness",
                "name": "Elderly Caregiving",
                "slug": "elderly-caregiving",
                "short_description": "Assisted daily living and companionship for seniors.",
                "bootstrap_icon": "bi-people",
                "theme_color": "#0D9488",
                "display_order": 4,
                "is_featured": False,
            },
            {
                "group": "healthcare-wellness",
                "name": "In-Home Lab Tests",
                "slug": "lab-sample-collection",
                "short_description": "Doorstep blood draw, diagnostic panels, and sample pickup.",
                "bootstrap_icon": "bi-droplet",
                "theme_color": "#0D9488",
                "display_order": 5,
                "is_featured": False,
            },
        ]
        categories_dict = {}
        for c in categories_data:
            group_slug = c.pop("group")
            cat_slug = c.pop("slug")
            group_obj = groups_dict[group_slug]
            cat, _ = Category.objects.update_or_create(
                slug=cat_slug,
                defaults={
                    "service_group": group_obj,
                    **c,
                },
            )
            categories_dict[cat_slug] = cat
            stats["categories"] += 1

        # --------------------------------------------------
        # STEP 3: SERVICES (14 Core Catalog Services)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Services...")
        services_data = [
            {
                "cat": "full-home-cleaning",
                "name": "Home Deep Cleaning",
                "slug": "home-deep-cleaning",
                "short_description": "Intensive multi-room deep cleaning, sanitization, and descaling.",
                "description": "Comprehensive cleaning package covering living areas, bedrooms, kitchen counters, and balconies with eco-friendly sanitizers and specialized machinery.",
                "starting_price": Decimal("1499.00"),
                "estimated_duration": "3-4 hours",
                "icon_class": "bi-stars",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "kitchen-bathroom-cleaning",
                "name": "Kitchen Deep Cleaning",
                "slug": "kitchen-deep-cleaning",
                "short_description": "Oil, grease removal, chimney wipe-down, and surface scrubbing.",
                "description": "Thorough degreasing of kitchen walls, gas burners, exhaust fans, tiled backsplashes, and storage exterior surfaces.",
                "starting_price": Decimal("699.00"),
                "estimated_duration": "2 hours",
                "icon_class": "bi-fire",
                "is_featured": True,
                "display_order": 2,
            },
            {
                "cat": "kitchen-bathroom-cleaning",
                "name": "Bathroom Deep Cleaning",
                "slug": "bathroom-deep-cleaning",
                "short_description": "Stain descaling, tile scrubbing, and fixture polishing.",
                "description": "Removal of hard water stains, deep tile scrubbing, mirror polishing, and sanitization of sanitaries.",
                "starting_price": Decimal("499.00"),
                "estimated_duration": "1-2 hours",
                "icon_class": "bi-droplet",
                "is_featured": False,
                "display_order": 3,
            },
            {
                "cat": "full-home-cleaning",
                "name": "Full Home Sanitization",
                "slug": "full-home-sanitization",
                "short_description": "Hospital-grade antiviral fogging and touchpoint sterilization.",
                "description": "Complete ULV fogging treatment targeting air pathways, high-touch furniture, doors, and surfaces to eliminate pathogens.",
                "starting_price": Decimal("899.00"),
                "estimated_duration": "1.5 hours",
                "icon_class": "bi-shield-check",
                "is_featured": False,
                "display_order": 4,
            },
            {
                "cat": "electrical-repair-cat",
                "name": "Electrical Switch & Socket Repair",
                "slug": "electrical-switch-repair",
                "short_description": "Fix loose contacts, sparking switches, and faulty power points.",
                "description": "Fast inspection and replacement of burnt switches, tripped MCBs, loose sockets, and internal box shorts.",
                "starting_price": Decimal("199.00"),
                "estimated_duration": "30-45 mins",
                "icon_class": "bi-lightning",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "wiring-installation",
                "name": "Ceiling Fan Installation & Repair",
                "slug": "ceiling-fan-installation",
                "short_description": "Assembly, rod mounting, regulator check, and balancing.",
                "description": "Expert ceiling fan mounting, downrod installation, blade balancing, regulator wiring, and wobble elimination.",
                "starting_price": Decimal("299.00"),
                "estimated_duration": "45 mins",
                "icon_class": "bi-fan",
                "is_featured": False,
                "display_order": 2,
            },
            {
                "cat": "wiring-installation",
                "name": "Complete Home Rewiring & Inspection",
                "slug": "complete-home-rewiring",
                "short_description": "Earth leakage test, distribution box upgrade, and rewiring.",
                "description": "Comprehensive electrical safety inspection, insulation resistance check, earthing verification, and wiring overhaul.",
                "starting_price": Decimal("1999.00"),
                "estimated_duration": "1 day",
                "icon_class": "bi-diagram-3",
                "is_featured": False,
                "display_order": 3,
            },
            {
                "cat": "plumbing-repair",
                "name": "Plumbing & Pipe Leakage Repair",
                "slug": "plumbing-leakage-repair",
                "short_description": "Fix leaking taps, burst pipes, angle valves, and flush tanks.",
                "description": "Immediate diagnostics and fixing of water leakage from CP fittings, concealed pipes, shower connections, and tanks.",
                "starting_price": Decimal("249.00"),
                "estimated_duration": "1 hour",
                "icon_class": "bi-tools",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "drainage-pipes",
                "name": "Drain Unclogging & Cleaning",
                "slug": "drain-unclogging-service",
                "short_description": "Clear blocked sinks, floor traps, and main drainage lines.",
                "description": "High-efficiency mechanized snake drilling and chemical flushing to unclog jammed kitchen and bathroom drains.",
                "starting_price": Decimal("349.00"),
                "estimated_duration": "1-2 hours",
                "icon_class": "bi-water",
                "is_featured": False,
                "display_order": 2,
            },
            {
                "cat": "ac-general-service-cat",
                "name": "AC General Service & Filter Cleaning",
                "slug": "ac-general-service",
                "short_description": "Foam jet service, blower wash, cooling coil inspection.",
                "description": "Specialized indoor jet wash, condenser fin cleaning, drainage tray unclogging, and operating pressure check.",
                "starting_price": Decimal("499.00"),
                "estimated_duration": "1 hour",
                "icon_class": "bi-snow2",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "ac-install-repair-cat",
                "name": "AC Installation & Setup",
                "slug": "ac-installation-uninstallation",
                "short_description": "Indoor bracket mounting, copper pipe laying, and vacuuming.",
                "description": "Precision mounting of split AC indoor & outdoor units, core drilling, flare connection, and gas pressure tuning.",
                "starting_price": Decimal("999.00"),
                "estimated_duration": "2-3 hours",
                "icon_class": "bi-wrench",
                "is_featured": False,
                "display_order": 2,
            },
            {
                "cat": "interior-painting-cat",
                "name": "Interior Wall Painting & Touch-up",
                "slug": "interior-wall-painting",
                "short_description": "Putty filling, primer coat, premium emulsion finish.",
                "description": "Professional residential painting with wall sanding, crack bridging, dual primer coat, and premium acrylic emulsion.",
                "starting_price": Decimal("2499.00"),
                "estimated_duration": "1-2 days",
                "icon_class": "bi-paint-bucket",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "salon-at-home",
                "name": "Men's Grooming & Haircut at Home",
                "slug": "mens-haircut-at-home",
                "short_description": "Precision haircut, beard trim, and relaxing scalp massage.",
                "description": "Hygienic at-home styling with sterilized tool kits, disposable capes, custom haircut, and beard grooming.",
                "starting_price": Decimal("299.00"),
                "estimated_duration": "45 mins",
                "icon_class": "bi-scissors",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "salon-at-home",
                "name": "Women's Spa & Beauty Package",
                "slug": "womens-salon-package",
                "short_description": "Facial, waxing, manicure, and pedicure relaxation session.",
                "description": "Luxury doorstep pampering with premium herbal skincare products, threading, and relaxing wellness rituals.",
                "starting_price": Decimal("799.00"),
                "estimated_duration": "2 hours",
                "icon_class": "bi-heart-pulse",
                "is_featured": False,
                "display_order": 2,
            },
            # Healthcare & Wellness Services (Phase 6)
            {
                "cat": "doctor-home-visit",
                "name": "Doctor In-Home Consultation & Checkup",
                "slug": "doctor-home-consultation",
                "short_description": "Licensed physician in-home clinical consultation, diagnosis, and vitals check.",
                "description": "Comprehensive at-home medical consultation by verified doctors including full vital signs assessment, medication review, clinical advice, and personalized care planning.",
                "starting_price": Decimal("799.00"),
                "estimated_duration": "45-60 mins",
                "icon_class": "bi-person-badge",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "home-nursing-care",
                "name": "Post-Operative Nursing & Wound Care",
                "slug": "post-operative-home-nursing",
                "short_description": "Registered nurse for sterile wound dressing, IV lines, and post-discharge recovery.",
                "description": "Skilled home nursing care provided by certified nurses for surgical dressing, catheter care, injections, medication administration, and vital parameter monitoring.",
                "starting_price": Decimal("599.00"),
                "estimated_duration": "1-2 hours",
                "icon_class": "bi-heart-pulse",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "physiotherapy-rehab",
                "name": "Orthopedic & Neuro Physiotherapy",
                "slug": "orthopedic-physiotherapy-session",
                "short_description": "Certified physiotherapist for mobility restoration, stroke rehab, and pain management.",
                "description": "Evidence-based at-home physiotherapy targeting joint arthritis, back pain, post-fracture mobility recovery, stroke rehabilitation, and muscle strengthening.",
                "starting_price": Decimal("699.00"),
                "estimated_duration": "60 mins",
                "icon_class": "bi-activity",
                "is_featured": True,
                "display_order": 1,
            },
            {
                "cat": "elderly-caregiving",
                "name": "Daily Assisted Senior Caregiving",
                "slug": "elderly-caregiving-daily",
                "short_description": "Trained geriatric companion for daily living assistance, mobility, and diet monitoring.",
                "description": "Compassionate, professional senior caregiving at home covering hygiene assistance, mobility support, medication reminders, companionship, and daily activity help.",
                "starting_price": Decimal("1199.00"),
                "estimated_duration": "4-8 hours",
                "icon_class": "bi-people",
                "is_featured": False,
                "display_order": 1,
            },
            {
                "cat": "lab-sample-collection",
                "name": "Full Body Health Checkup Blood Panel",
                "slug": "full-body-health-checkup-lab",
                "short_description": "Certified phlebotomist doorstep blood draw with NABL accredited lab report.",
                "description": "Convenient home sample collection for 64+ key diagnostic biomarkers (CBC, Lipid, Liver, Kidney, HbA1c, Thyroid) with digital NABL lab reports within 24 hours.",
                "starting_price": Decimal("1499.00"),
                "estimated_duration": "30 mins",
                "icon_class": "bi-droplet",
                "is_featured": False,
                "display_order": 1,
            },
        ]
        services_dict = {}
        for s in services_data:
            cat_slug = s.pop("cat")
            service_slug = s.pop("slug")
            cat_obj = categories_dict[cat_slug]
            service, _ = Service.objects.update_or_create(
                slug=service_slug,
                defaults={
                    "category": cat_obj,
                    "is_active": True,
                    **s,
                },
            )
            services_dict[service_slug] = service
            stats["services"] += 1

        # --------------------------------------------------
        # STEP 4: SERVICE PACKAGES & INCLUDES
        # --------------------------------------------------
        self.stdout.write("-> Seeding Service Packages & Includes...")
        # Common package structures for services
        packages_config = {
            "home-deep-cleaning": [
                {
                    "name": "1 BHK Deep Cleaning",
                    "slug": "1-bhk-deep-cleaning",
                    "short_description": "Ideal for 1 BHK flats and studio apartments.",
                    "price": Decimal("1499.00"),
                    "duration": timedelta(hours=3),
                    "is_popular": False,
                    "sort_order": 1,
                    "features": [
                        ("Dusting and wiping of all accessible surfaces", True),
                        ("Floor scrubbing with motorized rotary brush", True),
                        ("Kitchen counter, backsplash & sink descaling", True),
                        ("Bathroom tile & sanitary fixture deep cleaning", True),
                        ("Balcony sweeping and washdown", True),
                    ],
                },
                {
                    "name": "2 BHK Deep Cleaning",
                    "slug": "2-bhk-deep-cleaning",
                    "short_description": "Our most popular comprehensive cleaning package.",
                    "price": Decimal("2299.00"),
                    "duration": timedelta(hours=4, minutes=30),
                    "is_popular": True,
                    "sort_order": 2,
                    "features": [
                        ("2 Bedrooms, Living room & Dining area deep clean", True),
                        ("Both bathrooms deep descaling & sanitization", True),
                        ("Modular kitchen interior cabinet wipe (empty)", True),
                        ("Window glass wiping & track vacuuming", True),
                        ("Cobweb removal & door polishing", True),
                    ],
                },
                {
                    "name": "3 BHK Deep Cleaning",
                    "slug": "3-bhk-deep-cleaning",
                    "short_description": "Luxury comprehensive deep cleaning for large apartments.",
                    "price": Decimal("3199.00"),
                    "duration": timedelta(hours=6),
                    "is_popular": False,
                    "sort_order": 3,
                    "features": [
                        ("3 Bedrooms & all common areas scrubbed", True),
                        ("3 Bathrooms descaling & tile grout cleaning", True),
                        ("Complete kitchen degreasing & appliance wipe", True),
                        ("Sofa dry vacuuming & balcony high-pressure wash", True),
                        ("Full eco-friendly germicidal sanitization spray", True),
                    ],
                },
            ],
            "ac-general-service": [
                {
                    "name": "Single AC Service (1 Unit)",
                    "slug": "single-ac-service",
                    "short_description": "Standard foam jet cleaning for 1 split AC unit.",
                    "price": Decimal("499.00"),
                    "duration": timedelta(minutes=45),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("High-pressure water jet filter wash", True),
                        ("Indoor cooling coil foam cleaning", True),
                        ("Drain tray unclogging & pipe flushing", True),
                        ("Outdoor unit dry cleaning & air check", True),
                    ],
                },
                {
                    "name": "Double AC Combo (2 Units)",
                    "slug": "double-ac-combo",
                    "short_description": "Discounted package for 2 split or window AC units.",
                    "price": Decimal("899.00"),
                    "duration": timedelta(hours=1, minutes=30),
                    "is_popular": False,
                    "sort_order": 2,
                    "features": [
                        ("Full foam jet service on 2 units", True),
                        ("Condenser fin cleaning on both outdoor units", True),
                        ("Refrigerant gas pressure measurement check", True),
                        ("Cooling temperature diagnostic before & after", True),
                    ],
                },
            ],
            "plumbing-leakage-repair": [
                {
                    "name": "Standard Inspection & Minor Leak Fix",
                    "slug": "standard-leak-fix",
                    "short_description": "Fix up to 2 minor tap/valve leaks.",
                    "price": Decimal("249.00"),
                    "duration": timedelta(minutes=45),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("Tap cartridge replacement / washer fix", True),
                        ("Angle valve & connection pipe inspection", True),
                        ("Teflon sealing and pressure test", True),
                    ],
                },
                {
                    "name": "Major Line & Flush Tank Overhaul",
                    "slug": "major-plumbing-fix",
                    "short_description": "Concealed pipe repairs, flush tank overhaul, or mixer replacement.",
                    "price": Decimal("599.00"),
                    "duration": timedelta(hours=2),
                    "is_popular": False,
                    "sort_order": 2,
                    "features": [
                        ("Concealed wall leak diagnostic", True),
                        ("Flush valve / syphon kit installation", True),
                        ("Diverter / Wall mixer replacement labor", True),
                        ("Complete water pressure check across all taps", True),
                    ],
                },
            ],
            "electrical-switch-repair": [
                {
                    "name": "Up to 3 Switches / Sockets",
                    "slug": "switch-repair-basic",
                    "short_description": "Quick replacement of up to 3 faulty switches or sockets.",
                    "price": Decimal("199.00"),
                    "duration": timedelta(minutes=30),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("Switchboard opening and safety testing", True),
                        ("Replacement of up to 3 damaged switches/sockets", True),
                        ("Proper wire insulation & terminal tightening", True),
                    ],
                },
                {
                    "name": "Complete Board Overhaul (Up to 8 points)",
                    "slug": "switchboard-overhaul",
                    "short_description": "Complete rewiring and repair for an entire main switchboard.",
                    "price": Decimal("449.00"),
                    "duration": timedelta(hours=1),
                    "is_popular": False,
                    "sort_order": 2,
                    "features": [
                        ("Inspection of main feed line & breaker", True),
                        ("Replacement of up to 8 switches, sockets & indicators", True),
                        ("Internal copper bridging & neat dressing", True),
                        ("Earth continuity test on all connected sockets", True),
                    ],
                },
            ],
            "interior-wall-painting": [
                {
                    "name": "Single Room Touch-up & Repaint",
                    "slug": "single-room-painting",
                    "short_description": "Complete repaint of 1 standard bedroom or living area.",
                    "price": Decimal("2499.00"),
                    "duration": timedelta(hours=8),
                    "is_popular": False,
                    "sort_order": 1,
                    "features": [
                        ("Wall putty touchup for cracks and nail holes", True),
                        ("Machine sanding with dust extraction", True),
                        ("2 coats of premium acrylic emulsion paint", True),
                        ("Floor masking and post-paint clean up", True),
                    ],
                },
                {
                    "name": "2 BHK Full Interior Painting",
                    "slug": "2-bhk-painting",
                    "short_description": "Complete interior revamp for 2 BHK apartment walls & ceilings.",
                    "price": Decimal("7999.00"),
                    "duration": timedelta(days=2),
                    "is_popular": True,
                    "sort_order": 2,
                    "features": [
                        ("Complete surface prep and primer coating", True),
                        ("2 coats of washable luxury interior paint", True),
                        ("Ceiling painting in bright ceiling white", True),
                        ("Furniture masking with heavy-duty drop sheets", True),
                        ("1-year LocalHub workmanship warranty", True),
                    ],
                },
            ],
            "mens-haircut-at-home": [
                {
                    "name": "Classic Haircut & Beard Trim",
                    "slug": "classic-haircut-beard",
                    "short_description": "Precision haircut and custom beard shaping.",
                    "price": Decimal("299.00"),
                    "duration": timedelta(minutes=45),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("Sterilized tools & disposable apron", True),
                        ("Personalized consultation & haircut", True),
                        ("Beard trimming, edging, and post-shave balm", True),
                        ("Head cleanup & hair vacuuming", True),
                    ],
                },
                {
                    "name": "Executive Royal Grooming Combo",
                    "slug": "executive-grooming",
                    "short_description": "Haircut, beard styling, charcoal face scrub, and scalp massage.",
                    "price": Decimal("599.00"),
                    "duration": timedelta(hours=1, minutes=15),
                    "is_popular": False,
                    "sort_order": 2,
                    "features": [
                        ("Classic haircut with hair wash setup", True),
                        ("Beard styling with hot towel treatment", True),
                        ("De-tan charcoal face pack & massage", True),
                        ("10-minute relaxing neck & scalp massage", True),
                    ],
                },
            ],
            # Healthcare Packages (Phase 6)
            "doctor-home-consultation": [
                {
                    "name": "Single Doctor Consultation & Vitals",
                    "slug": "single-doctor-visit",
                    "short_description": "General physician home visit for acute illness, fever, or follow-up.",
                    "price": Decimal("799.00"),
                    "duration": timedelta(minutes=45),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("Comprehensive medical history & physical examination", True),
                        ("Full vital signs check (BP, Pulse, Temp, SpO2, Blood Sugar)", True),
                        ("Prescription medication review & clinical advice", True),
                        ("Structured digital clinical visit summary note", True),
                    ],
                },
                {
                    "name": "Comprehensive Geriatric Health Review",
                    "slug": "geriatric-health-review",
                    "short_description": "Extended 75-min senior assessment with cognitive & mobility checks.",
                    "price": Decimal("1299.00"),
                    "duration": timedelta(hours=1, minutes=15),
                    "is_popular": False,
                    "sort_order": 2,
                    "features": [
                        ("Full physician examination + geriatric assessment", True),
                        ("Polypharmacy & prescription safety audit", True),
                        ("Fall risk & mobility independence evaluation", True),
                        ("Detailed family consultation & long-term care plan", True),
                    ],
                },
            ],
            "post-operative-home-nursing": [
                {
                    "name": "Single Nursing Visit (Wound / Injection)",
                    "slug": "single-nursing-visit",
                    "short_description": "Sterile wound dressing change, IV/IM injection, or catheter care.",
                    "price": Decimal("599.00"),
                    "duration": timedelta(hours=1),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("Aseptic sterile surgical dressing change", True),
                        ("Doctor-prescribed IV / IM injection administration", True),
                        ("Vital signs parameter log & surgical site assessment", True),
                        ("Infection warning signs guidance for patient", True),
                    ],
                },
            ],
            "orthopedic-physiotherapy-session": [
                {
                    "name": "Single Mobility & Pain Rehab Session",
                    "slug": "single-physio-session",
                    "short_description": "Targeted manual therapy, electrotherapy (TENS/IFT), and exercise.",
                    "price": Decimal("699.00"),
                    "duration": timedelta(minutes=60),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        ("Musculoskeletal joint assessment & range of motion test", True),
                        ("Targeted manual therapy & pain relief techniques", True),
                        ("Custom home exercise prescription & posture correction", True),
                        ("Progress tracking & mobility score evaluation", True),
                    ],
                },
            ],
        }

        # Seed packages for configured services, plus default 2-tier packages for all other services
        packages_dict = {}
        for s_slug, s_obj in services_dict.items():
            configs = packages_config.get(s_slug, [
                {
                    "name": "Standard Package",
                    "slug": "standard-package",
                    "short_description": f"Standard {s_obj.name} with certified professional tools.",
                    "price": s_obj.starting_price,
                    "duration": timedelta(hours=1),
                    "is_popular": True,
                    "sort_order": 1,
                    "features": [
                        (f"Professional inspection and {s_obj.name}", True),
                        ("All standard equipment and labor included", True),
                        ("Post-service quality checklist verification", True),
                    ],
                },
                {
                    "name": "Premium / Comprehensive Package",
                    "slug": "premium-package",
                    "short_description": f"Extended coverage and priority support for {s_obj.name}.",
                    "price": s_obj.starting_price * Decimal("1.6"),
                    "duration": timedelta(hours=2),
                    "is_popular": False,
                    "sort_order": 2,
                    "features": [
                        ("Comprehensive diagnostics and extended servicing", True),
                        ("Deep clean / precision finishing included", True),
                        ("30-day LocalHub service guarantee", True),
                    ],
                },
            ])

            for p_cfg in configs:
                features = p_cfg.pop("features")
                pkg, _ = ServicePackage.objects.update_or_create(
                    service=s_obj,
                    slug=p_cfg["slug"],
                    defaults={
                        "name": p_cfg["name"],
                        "short_description": p_cfg["short_description"],
                        "description": p_cfg["short_description"],
                        "price": p_cfg["price"],
                        "duration": p_cfg["duration"],
                        "is_popular": p_cfg.get("is_popular", False),
                        "is_active": True,
                        "sort_order": p_cfg.get("sort_order", 1),
                    },
                )
                packages_dict[f"{s_slug}:{pkg.slug}"] = pkg
                stats["packages"] += 1

                for idx, (title, _) in enumerate(features, start=1):
                    ServicePackageInclude.objects.update_or_create(
                        package=pkg,
                        title=title,
                        defaults={
                            "icon": "bi-check2",
                            "sort_order": idx,
                        },
                    )
                    stats["package_includes"] += 1

        # --------------------------------------------------
        # STEP 5: SERVICE REQUIREMENTS & FAQS
        # --------------------------------------------------
        self.stdout.write("-> Seeding Service Requirements & FAQs...")
        requirements_config = {
            "home-deep-cleaning": [
                {
                    "label": "Number of Bedrooms",
                    "field_name": "bedrooms_count",
                    "field_type": RequirementFieldType.SELECT,
                    "choices": ["1 BHK", "2 BHK", "3 BHK", "4+ BHK / Villa"],
                    "default_value": "2 BHK",
                    "required": True,
                    "sort_order": 1,
                },
                {
                    "label": "Property Occupancy Status",
                    "field_name": "occupancy_status",
                    "field_type": RequirementFieldType.RADIO,
                    "choices": ["Furnished / Occupied", "Unfurnished / Empty / Move-in"],
                    "default_value": "Furnished / Occupied",
                    "required": True,
                    "sort_order": 2,
                },
            ],
            "ac-general-service": [
                {
                    "label": "AC Unit Type",
                    "field_name": "ac_type",
                    "field_type": RequirementFieldType.SELECT,
                    "choices": ["Split AC", "Window AC", "Inverter AC"],
                    "default_value": "Split AC",
                    "required": True,
                    "sort_order": 1,
                },
                {
                    "label": "Known Issues or Symptoms",
                    "field_name": "ac_symptoms",
                    "field_type": RequirementFieldType.TEXT,
                    "placeholder": "e.g. Low cooling, water leakage, strange noise",
                    "required": False,
                    "sort_order": 2,
                },
            ],
            "interior-wall-painting": [
                {
                    "label": "Approximate Carpet Area (Sq Ft)",
                    "field_name": "carpet_area",
                    "field_type": RequirementFieldType.NUMBER,
                    "placeholder": "e.g. 850",
                    "default_value": "800",
                    "required": True,
                    "sort_order": 1,
                },
            ],
        }

        for s_slug, reqs in requirements_config.items():
            s_obj = services_dict.get(s_slug)
            if s_obj:
                for r in reqs:
                    field_name = r.pop("field_name")
                    ServiceRequirement.objects.update_or_create(
                        service=s_obj,
                        field_name=field_name,
                        defaults={"is_active": True, **r},
                    )
                    stats["requirements"] += 1

        faqs_config = {
            "home-deep-cleaning": [
                ("How long does the deep cleaning service take?", "A standard 2 BHK deep clean takes between 3.5 to 5 hours depending on the property layout and buildup."),
                ("Do I need to supply cleaning liquids or equipment?", "No, our verified LocalHub cleaning professionals bring all required industrial vacuums, single-disc scrubbers, microfiber cloths, and specialized eco-friendly chemicals."),
                ("Can I stay at home while the cleaning is in progress?", "Yes, you are welcome to stay. Our team uses non-toxic, pet-safe chemicals that do not release hazardous fumes."),
            ],
            "ac-general-service": [
                ("How frequently should I get my AC serviced?", "For optimal cooling and energy efficiency, we recommend a general foam jet service every 4 to 6 months."),
                ("Does general service include gas refilling?", "General service includes gas pressure checks. If a top-up or repair is required due to low pressure, our technician will provide an exact quote before proceeding."),
            ],
            "plumbing-leakage-repair": [
                ("Are replacement spare parts included in the price?", "The service fee covers professional diagnosis and labor. If replacement spare parts (e.g. valves, washers, faucets) are needed, you may supply them or our pro can purchase them with your consent at actual MRP."),
                ("What if the leakage recurs after repair?", "All plumbing services on LocalHub come with a 15-day workmanship guarantee. If the same fix leaks within 15 days, we re-inspect free of charge."),
            ],
            "electrical-switch-repair": [
                ("Is it safe to get high-voltage electrical repairs done at home?", "Yes. All LocalHub electrical technicians are background-checked, certified professionals equipped with insulated Class-0 safety tools, voltage detectors, and protective gear."),
            ],
        }

        for s_slug, faqs in faqs_config.items():
            s_obj = services_dict.get(s_slug)
            if s_obj:
                for idx, (q, a) in enumerate(faqs, start=1):
                    ServiceFAQ.objects.update_or_create(
                        service=s_obj,
                        question=q,
                        defaults={
                            "answer": a,
                            "sort_order": idx,
                        },
                    )
                    stats["faqs"] += 1

        # --------------------------------------------------
        # STEP 6: USERS (Admin, Customers, Professionals)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Users, Profiles, and Addresses...")
        
        # 6.1 Admin User
        admin_user, _ = User.objects.update_or_create(
            email=self.SEED_ADMIN_EMAIL,
            defaults={
                "first_name": "LocalHub",
                "last_name": "Administrator",
                "phone": "+919800000001",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "is_email_verified": True,
                "is_phone_verified": True,
                "profile_completed": True,
            },
        )
        admin_user.set_password(self.DEV_PASSWORD)
        admin_user.save()

        # Update Admin Profile
        admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
        admin_profile.display_name = "Operations Admin"
        admin_profile.occupation = "Platform Manager"
        admin_profile.city = "Kochi"
        admin_profile.state = "Kerala"
        admin_profile.country = "India"
        admin_profile.save()

        # 6.2 Customer Users
        customers_info = [
            {
                "email": "customer@localhub.com",
                "first_name": "Alex",
                "last_name": "Mathew",
                "phone": "+919876543210",
                "city": "Kochi",
                "address": {
                    "full_name": "Alex Mathew",
                    "phone": "+919876543210",
                    "address_type": Address.AddressType.HOME,
                    "house_name": "Apt 4B, Skyline Riverdale",
                    "area": "Panampilly Nagar",
                    "landmark": "Near Central Park",
                    "city": "Kochi",
                    "state": "Kerala",
                    "postal_code": "682036",
                    "is_default": True,
                },
            },
            {
                "email": "sarah.customer@localhub.com",
                "first_name": "Sarah",
                "last_name": "Philip",
                "phone": "+919876543211",
                "city": "Trivandrum",
                "address": {
                    "full_name": "Sarah Philip",
                    "phone": "+919876543211",
                    "address_type": Address.AddressType.HOME,
                    "house_name": "Villa 12, Kowdiar Palms",
                    "area": "Kowdiar",
                    "landmark": "Opposite Golf Club",
                    "city": "Trivandrum",
                    "state": "Kerala",
                    "postal_code": "695003",
                    "is_default": True,
                },
            },
            {
                "email": "arjun.customer@localhub.com",
                "first_name": "Arjun",
                "last_name": "Nair",
                "phone": "+919876543212",
                "city": "Calicut",
                "address": {
                    "full_name": "Arjun Nair",
                    "phone": "+919876543212",
                    "address_type": Address.AddressType.HOME,
                    "house_name": "Green Valley House",
                    "area": "Mavoor Road",
                    "landmark": "Near Arayidathupalam",
                    "city": "Calicut",
                    "state": "Kerala",
                    "postal_code": "673004",
                    "is_default": True,
                },
            },
        ]

        customers_dict = {}
        for c in customers_info:
            addr_data = c.pop("address")
            cust_user, _ = User.objects.update_or_create(
                email=c["email"],
                defaults={
                    "first_name": c["first_name"],
                    "last_name": c["last_name"],
                    "phone": c["phone"],
                    "role": User.Role.CUSTOMER,
                    "is_active": True,
                    "is_email_verified": True,
                    "is_phone_verified": True,
                    "profile_completed": True,
                },
            )
            cust_user.set_password(self.DEV_PASSWORD)
            cust_user.save()

            # Profile
            c_prof, _ = UserProfile.objects.get_or_create(user=cust_user)
            c_prof.display_name = f"{cust_user.first_name} {cust_user.last_name}"
            c_prof.city = c["city"]
            c_prof.state = "Kerala"
            c_prof.country = "India"
            c_prof.save()

            # Address
            addr, _ = Address.objects.update_or_create(
                user=cust_user,
                house_name=addr_data["house_name"],
                defaults=addr_data,
            )
            customers_dict[c["email"]] = {
                "user": cust_user,
                "profile": c_prof,
                "address": addr,
            }
            stats["customers"] += 1
            stats["addresses"] += 1

        # 6.3 Professional Users & Professional Profiles
        workers_info = [
            {
                "email": "rahul.electrician@localhub.com",
                "first_name": "Rahul",
                "last_name": "Menon",
                "phone": "+919845000001",
                "city": "Kochi",
                "title": "Certified Master Electrician",
                "bio": "Licensed electrical specialist with 6+ years of residential rewiring, smart home installations, and circuit safety diagnostics experience.",
                "experience_years": 6,
                "hourly_rate": Decimal("299.00"),
                "minimum_charge": Decimal("199.00"),
                "working_radius": 15,
                "skills": ["electrical-repair", "switch-socket-repair", "appliance-repair"],
                "languages": ["en", "ml", "hi"],
                "services": [
                    ("electrical-switch-repair", Decimal("199.00"), timedelta(minutes=45)),
                    ("ceiling-fan-installation", Decimal("299.00"), timedelta(minutes=45)),
                    ("complete-home-rewiring", Decimal("1999.00"), timedelta(hours=8)),
                ],
                "verified": True,
            },
            {
                "email": "ameen.plumber@localhub.com",
                "first_name": "Ameen",
                "last_name": "Rahman",
                "phone": "+919845000002",
                "city": "Kochi",
                "title": "Senior Plumbing Specialist",
                "bio": "Expert in high-pressure plumbing, pipe leak localization, concealed drainage lines, and sanitary installation across Kochi.",
                "experience_years": 8,
                "hourly_rate": Decimal("349.00"),
                "minimum_charge": Decimal("249.00"),
                "working_radius": 20,
                "skills": ["plumbing", "pipe-fitting", "drain-cleaning"],
                "languages": ["en", "ml", "ta"],
                "services": [
                    ("plumbing-leakage-repair", Decimal("249.00"), timedelta(hours=1)),
                    ("drain-unclogging-service", Decimal("349.00"), timedelta(hours=1, minutes=30)),
                ],
                "verified": True,
            },
            {
                "email": "jithin.actech@localhub.com",
                "first_name": "Jithin",
                "last_name": "Kumar",
                "phone": "+919845000003",
                "city": "Trivandrum",
                "title": "HVAC & AC Service Engineer",
                "bio": "Certified refrigeration and AC technician specializing in split unit jet servicing, compressor repairs, and precision installations.",
                "experience_years": 5,
                "hourly_rate": Decimal("399.00"),
                "minimum_charge": Decimal("299.00"),
                "working_radius": 25,
                "skills": ["ac-maintenance", "ac-installation", "appliance-repair"],
                "languages": ["en", "ml", "hi"],
                "services": [
                    ("ac-general-service", Decimal("499.00"), timedelta(hours=1)),
                    ("ac-installation-uninstallation", Decimal("999.00"), timedelta(hours=2, minutes=30)),
                ],
                "verified": True,
            },
            {
                "email": "nisha.beauty@localhub.com",
                "first_name": "Nisha",
                "last_name": "Thomas",
                "phone": "+919845000004",
                "city": "Kochi",
                "title": "Professional Beautician & Stylist",
                "bio": "Salon professional providing hygienic grooming, skincare, hair styling, and relaxing wellness rituals at home.",
                "experience_years": 7,
                "hourly_rate": Decimal("499.00"),
                "minimum_charge": Decimal("299.00"),
                "working_radius": 15,
                "skills": ["beauty-services"],
                "languages": ["en", "ml"],
                "services": [
                    ("mens-haircut-at-home", Decimal("299.00"), timedelta(minutes=45)),
                    ("womens-salon-package", Decimal("799.00"), timedelta(hours=2)),
                ],
                "verified": True,
            },
            {
                "email": "vikram.painter@localhub.com",
                "first_name": "Vikram",
                "last_name": "Das",
                "phone": "+919845000005",
                "city": "Calicut",
                "title": "Interior Painting & Wall Specialist",
                "bio": "Skilled painter focusing on texture walls, waterproofing, smooth putty finishes, and residential renovation.",
                "experience_years": 4,
                "hourly_rate": Decimal("399.00"),
                "minimum_charge": Decimal("499.00"),
                "working_radius": 20,
                "skills": ["interior-painting", "deep-cleaning"],
                "languages": ["en", "ml", "hi"],
                "services": [
                    ("interior-wall-painting", Decimal("2499.00"), timedelta(hours=8)),
                    ("home-deep-cleaning", Decimal("1499.00"), timedelta(hours=4)),
                ],
                "verified": False,  # Kept in Pending / Under Review state for admin triage testing
            },
            # Healthcare Professionals (Phase 6)
            {
                "email": "dr.kavita.doctor@localhub.com",
                "first_name": "Kavita",
                "last_name": "Shenoy",
                "phone": "+919845000006",
                "city": "Kochi",
                "title": "Consultant Physician (MBBS, MD)",
                "bio": "Board-certified general physician with 10+ years of clinical experience in geriatric care, chronic illness management, and home medical consultations.",
                "experience_years": 10,
                "hourly_rate": Decimal("799.00"),
                "minimum_charge": Decimal("799.00"),
                "working_radius": 20,
                "skills": ["general-medicine", "elder-care"],
                "languages": ["en", "ml", "hi"],
                "services": [
                    ("doctor-home-consultation", Decimal("799.00"), timedelta(minutes=45)),
                ],
                "verified": True,
            },
            {
                "email": "sister.mary.nurse@localhub.com",
                "first_name": "Mary",
                "last_name": "Varghese",
                "phone": "+919845000007",
                "city": "Kochi",
                "title": "Registered Critical Care & Home Nurse",
                "bio": "Certified clinical nurse with 8+ years experience in sterile surgical wound dressing, catheter management, IV therapy, and post-operative home recovery.",
                "experience_years": 8,
                "hourly_rate": Decimal("599.00"),
                "minimum_charge": Decimal("499.00"),
                "working_radius": 25,
                "skills": ["clinical-nursing", "elder-care", "phlebotomy"],
                "languages": ["en", "ml", "hi"],
                "services": [
                    ("post-operative-home-nursing", Decimal("599.00"), timedelta(hours=1)),
                    ("elderly-caregiving-daily", Decimal("1199.00"), timedelta(hours=6)),
                ],
                "verified": True,
            },
            {
                "email": "rohit.physio@localhub.com",
                "first_name": "Rohit",
                "last_name": "Nair",
                "phone": "+919845000008",
                "city": "Kochi",
                "title": "Consultant Physiotherapist (MPT Ortho)",
                "bio": "Specialist physiotherapist delivering tailored at-home mobility rehabilitation, joint mobilization, pain management, and stroke recovery.",
                "experience_years": 7,
                "hourly_rate": Decimal("699.00"),
                "minimum_charge": Decimal("699.00"),
                "working_radius": 20,
                "skills": ["physiotherapy", "elder-care"],
                "languages": ["en", "ml", "ta"],
                "services": [
                    ("orthopedic-physiotherapy-session", Decimal("699.00"), timedelta(hours=1)),
                ],
                "verified": True,
            },
        ]

        workers_dict = {}
        for w in workers_info:
            w_user, _ = User.objects.update_or_create(
                email=w["email"],
                defaults={
                    "first_name": w["first_name"],
                    "last_name": w["last_name"],
                    "phone": w["phone"],
                    "role": User.Role.PROFESSIONAL,
                    "is_active": True,
                    "is_email_verified": True,
                    "is_phone_verified": True,
                    "profile_completed": True,
                },
            )
            w_user.set_password(self.DEV_PASSWORD)
            w_user.save()

            # Profile
            w_prof, _ = UserProfile.objects.get_or_create(user=w_user)
            w_prof.display_name = f"{w['first_name']} {w['last_name']}"
            w_prof.bio = w["bio"]
            w_prof.city = w["city"]
            w_prof.state = "Kerala"
            w_prof.country = "India"
            w_prof.save()

            # Professional Profile
            pro_profile, _ = ProfessionalProfile.objects.update_or_create(
                user=w_user,
                defaults={
                    "professional_title": w["title"],
                    "bio": w["bio"],
                    "experience_years": w["experience_years"],
                    "hourly_rate": w["hourly_rate"],
                    "minimum_charge": w["minimum_charge"],
                    "working_radius": w["working_radius"],
                    "availability_status": ProfessionalProfile.AvailabilityStatus.AVAILABLE,
                    "average_rating": Decimal("4.90"),
                    "reviews_count": 0,
                },
            )

            # Assign Skills & Languages
            for s_k in w["skills"]:
                if s_k in skills_dict:
                    pro_profile.skills.add(skills_dict[s_k])
            for l_k in w["languages"]:
                if l_k in languages_dict:
                    pro_profile.languages.add(languages_dict[l_k])

            # Map Professional Services
            for s_slug, custom_price, est_duration in w["services"]:
                s_obj = services_dict.get(s_slug)
                if s_obj:
                    ProfessionalService.objects.update_or_create(
                        professional=pro_profile,
                        service=s_obj,
                        defaults={
                            "custom_price": custom_price,
                            "estimated_duration": est_duration,
                            "is_active": True,
                            "is_featured": True,
                            "display_order": 1,
                        },
                    )
                    stats["professional_services"] += 1

            workers_dict[w["email"]] = {
                "user": w_user,
                "profile": pro_profile,
                "verified": w["verified"],
            }
            stats["professionals"] += 1

        # --------------------------------------------------
        # STEP 7: PROFESSIONAL VERIFICATION & KYC WORKFLOW
        # --------------------------------------------------
        self.stdout.write("-> Seeding Verification & KYC records...")
        now = timezone.now()
        dummy_pdf_content = b"%PDF-1.4\n%LocalHub Verified Development Document Placeholder\n%%EOF\n"

        for email, w_data in workers_dict.items():
            pro_profile = w_data["profile"]
            is_verified = w_data["verified"]

            # Fetch or create verification
            verification, _ = ProfessionalVerification.objects.get_or_create(
                professional=pro_profile,
            )

            if is_verified:
                verification.status = VerificationStatus.APPROVED
                verification.submitted_at = now - timedelta(days=30)
                verification.reviewed_at = now - timedelta(days=29)
                verification.reviewed_by = admin_user
                verification.rejection_reason = ""
                verification.save()

                # Upload safe development placeholder document
                doc_type = DocumentType.EXPERIENCE_CERTIFICATE
                doc_num = "CERT-DEV-2026"
                if "doctor" in email:
                    doc_type = DocumentType.MEDICAL_COUNCIL_REGISTRATION
                    doc_num = "KMC-2015-88412"
                elif "nurse" in email:
                    doc_type = DocumentType.NURSING_COUNCIL_LICENSE
                    doc_num = "KNC-2017-45910"
                elif "physio" in email:
                    doc_type = DocumentType.CLINICAL_DEGREE
                    doc_num = "IAP-2018-12903"

                doc, _ = ProfessionalVerificationDocument.objects.update_or_create(
                    verification=verification,
                    document_type=doc_type,
                    document_number=doc_num,
                    defaults={
                        "status": DocumentStatus.VERIFIED,
                        "reviewed_by": admin_user,
                        "reviewed_at": now - timedelta(days=29),
                    },
                )
                if not doc.document_file:
                    doc.document_file.save("dev_experience_cert.pdf", ContentFile(dummy_pdf_content), save=True)
                stats["verification_documents"] += 1

                # History Logs
                VerificationHistoryLog.objects.create(
                    verification=verification,
                    previous_status=VerificationStatus.DRAFT,
                    new_status=VerificationStatus.PENDING,
                    action="submitted",
                    performed_by=pro_profile.user,
                    notes="Professional submitted credentials for verification.",
                )
                VerificationHistoryLog.objects.create(
                    verification=verification,
                    previous_status=VerificationStatus.PENDING,
                    new_status=VerificationStatus.APPROVED,
                    action="approved",
                    performed_by=admin_user,
                    notes="Admin reviewed and verified professional credentials.",
                )
                stats["verification_history"] += 2
            else:
                # Pending / Under Review Pro for Admin Dashboard test
                verification.status = VerificationStatus.UNDER_REVIEW
                verification.submitted_at = now - timedelta(days=2)
                verification.reviewed_at = now - timedelta(hours=4)
                verification.reviewed_by = admin_user
                verification.save()

                doc, _ = ProfessionalVerificationDocument.objects.update_or_create(
                    verification=verification,
                    document_type=DocumentType.TRADE_LICENSE,
                    document_number="LIC-DEV-2026",
                    defaults={
                        "status": DocumentStatus.PENDING,
                    },
                )
                if not doc.document_file:
                    doc.document_file.save("dev_trade_license.pdf", ContentFile(dummy_pdf_content), save=True)
                stats["verification_documents"] += 1

                VerificationHistoryLog.objects.create(
                    verification=verification,
                    previous_status=VerificationStatus.DRAFT,
                    new_status=VerificationStatus.PENDING,
                    action="submitted",
                    performed_by=pro_profile.user,
                    notes="Application submitted with trade license documentation.",
                )
                stats["verification_history"] += 1

            stats["verifications"] += 1

        # --------------------------------------------------
        # STEP 8: BOOKINGS & STATUS HISTORY (10 Demo Bookings)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Bookings & Lifecycle Histories...")
        alex = customers_dict["customer@localhub.com"]
        sarah = customers_dict["sarah.customer@localhub.com"]
        arjun = customers_dict["arjun.customer@localhub.com"]

        rahul = workers_dict["rahul.electrician@localhub.com"]
        ameen = workers_dict["ameen.plumber@localhub.com"]
        jithin = workers_dict["jithin.actech@localhub.com"]
        nisha = workers_dict["nisha.beauty@localhub.com"]

        today = date.today()

        bookings_config = [
            # 1. Completed Deep Clean - Alex & Vikram/Rahul
            {
                "number": "BK-2026-1001",
                "customer": alex["user"],
                "worker": rahul["user"],
                "service": services_dict["home-deep-cleaning"],
                "package": packages_dict["home-deep-cleaning:2-bhk-deep-cleaning"],
                "address": alex["address"],
                "date": today - timedelta(days=14),
                "start": time(9, 30),
                "end": time(14, 0),
                "status": BookingStatus.COMPLETED,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("2299.00"),
                "total": Decimal("2299.00"),
                "note": "Please pay special attention to the balcony sliding glass.",
                "history": [
                    (BookingStatus.PENDING, "Booking placed by customer.", "customer"),
                    (BookingStatus.WORKER_ASSIGNED, "Rahul Menon assigned to service.", "system"),
                    (BookingStatus.ARRIVED, "Professional arrived at premises.", "worker"),
                    (BookingStatus.IN_PROGRESS, "Deep cleaning started.", "worker"),
                    (BookingStatus.COMPLETED, "Deep cleaning finished with customer sign-off.", "worker"),
                ],
                "review": {
                    "rating": 5,
                    "comment": "Outstanding cleaning! The team cleaned every corner of our 2 BHK thoroughly. Very professional.",
                    "reply": "Thank you Alex! It was our pleasure to serve you. Happy to help anytime!",
                },
            },
            # 2. Completed AC Service - Sarah & Jithin
            {
                "number": "BK-2026-1002",
                "customer": sarah["user"],
                "worker": jithin["user"],
                "service": services_dict["ac-general-service"],
                "package": packages_dict["ac-general-service:single-ac-service"],
                "address": sarah["address"],
                "date": today - timedelta(days=10),
                "start": time(11, 0),
                "end": time(12, 0),
                "status": BookingStatus.COMPLETED,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("499.00"),
                "total": Decimal("499.00"),
                "note": "Living room split AC cooling feels weak.",
                "history": [
                    (BookingStatus.PENDING, "Booking confirmed.", "customer"),
                    (BookingStatus.WORKER_ASSIGNED, "Jithin Kumar assigned.", "system"),
                    (BookingStatus.COMPLETED, "AC filter and jet wash completed.", "worker"),
                ],
                "review": {
                    "rating": 5,
                    "comment": "Jithin arrived exactly on time and did a thorough foam jet wash. AC cooling is back to 100%!",
                    "reply": "Glad to hear that Sarah! Ensure regular filter cleaning for optimal efficiency.",
                },
            },
            # 3. Completed Plumbing Repair - Alex & Ameen
            {
                "number": "BK-2026-1003",
                "customer": alex["user"],
                "worker": ameen["user"],
                "service": services_dict["plumbing-leakage-repair"],
                "package": packages_dict["plumbing-leakage-repair:standard-leak-fix"],
                "address": alex["address"],
                "date": today - timedelta(days=6),
                "start": time(15, 0),
                "end": time(16, 0),
                "status": BookingStatus.COMPLETED,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("249.00"),
                "total": Decimal("249.00"),
                "note": "Kitchen tap dripping continuously.",
                "history": [
                    (BookingStatus.PENDING, "Booking created.", "customer"),
                    (BookingStatus.WORKER_ASSIGNED, "Ameen Rahman assigned.", "system"),
                    (BookingStatus.COMPLETED, "Tap cartridge replaced.", "worker"),
                ],
                "review": {
                    "rating": 4,
                    "comment": "Fixed the leakage in 20 minutes neatly. Good pricing and quick turnaround.",
                    "reply": "Thank you for trusting LocalHub plumbing services!",
                },
            },
            # 4. Completed Men's Grooming - Arjun & Nisha
            {
                "number": "BK-2026-1004",
                "customer": arjun["user"],
                "worker": nisha["user"],
                "service": services_dict["mens-haircut-at-home"],
                "package": packages_dict["mens-haircut-at-home:classic-haircut-beard"],
                "address": arjun["address"],
                "date": today - timedelta(days=4),
                "start": time(16, 30),
                "end": time(17, 15),
                "status": BookingStatus.COMPLETED,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("299.00"),
                "total": Decimal("299.00"),
                "note": "Fade cut on sides please.",
                "history": [
                    (BookingStatus.PENDING, "Booking confirmed.", "customer"),
                    (BookingStatus.COMPLETED, "Haircut and beard trim done.", "worker"),
                ],
                "review": {
                    "rating": 5,
                    "comment": "Convenient doorstep haircut. Great attention to detail and sanitized equipment.",
                    "reply": "Appreciate your kind feedback Arjun!",
                },
            },
            # 5. Completed Electrical Repair - Sarah & Rahul
            {
                "number": "BK-2026-1005",
                "customer": sarah["user"],
                "worker": rahul["user"],
                "service": services_dict["electrical-switch-repair"],
                "package": packages_dict["electrical-switch-repair:switch-repair-basic"],
                "address": sarah["address"],
                "date": today - timedelta(days=2),
                "start": time(10, 0),
                "end": time(10, 45),
                "status": BookingStatus.COMPLETED,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("199.00"),
                "total": Decimal("199.00"),
                "note": "Bedroom 2 switch sparking when turning on AC.",
                "history": [
                    (BookingStatus.PENDING, "Booking received.", "customer"),
                    (BookingStatus.COMPLETED, "Sparking switch and box wire replaced.", "worker"),
                ],
                "review": {
                    "rating": 5,
                    "comment": "Rahul explained the issue clearly and fixed the switch safely. Very impressed.",
                    "reply": "Safety first! Always glad to assist.",
                },
                "report": {
                    "reason": ReportReason.OTHER,
                    "desc": "Testing admin review report moderation pipeline.",
                },
            },
            # 6. In Progress Today - Alex & Jithin (AC Install)
            {
                "number": "BK-2026-1006",
                "customer": alex["user"],
                "worker": jithin["user"],
                "service": services_dict["ac-installation-uninstallation"],
                "package": packages_dict["ac-installation-uninstallation:standard-package"],
                "address": alex["address"],
                "date": today,
                "start": time(10, 0),
                "end": time(12, 30),
                "status": BookingStatus.IN_PROGRESS,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("999.00"),
                "total": Decimal("999.00"),
                "note": "New 1.5 ton split AC installation in master bedroom.",
                "history": [
                    (BookingStatus.PENDING, "Booking scheduled.", "customer"),
                    (BookingStatus.WORKER_ASSIGNED, "Jithin Kumar assigned.", "system"),
                    (BookingStatus.ARRIVED, "Technician arrived on site.", "worker"),
                    (BookingStatus.IN_PROGRESS, "Bracket mounting & copper piping in progress.", "worker"),
                ],
            },
            # 7. Worker Assigned (Upcoming Tomorrow) - Sarah & Ameen (Drain Clean)
            {
                "number": "BK-2026-1007",
                "customer": sarah["user"],
                "worker": ameen["user"],
                "service": services_dict["drain-unclogging-service"],
                "package": packages_dict["drain-unclogging-service:standard-package"],
                "address": sarah["address"],
                "date": today + timedelta(days=1),
                "start": time(14, 0),
                "end": time(15, 30),
                "status": BookingStatus.WORKER_ASSIGNED,
                "payment": PaymentStatus.UNPAID,
                "subtotal": Decimal("349.00"),
                "total": Decimal("349.00"),
                "note": "Kitchen drain slow water drainage.",
                "history": [
                    (BookingStatus.PENDING, "Booking placed by customer.", "customer"),
                    (BookingStatus.WORKER_ASSIGNED, "Ameen Rahman accepted job assignment.", "worker"),
                ],
            },
            # 8. Pending New Dispatch - Arjun (Painting Inspection)
            {
                "number": "BK-2026-1008",
                "customer": arjun["user"],
                "worker": None,
                "service": services_dict["interior-wall-painting"],
                "package": packages_dict["interior-wall-painting:single-room-painting"],
                "address": arjun["address"],
                "date": today + timedelta(days=3),
                "start": time(10, 0),
                "end": time(18, 0),
                "status": BookingStatus.PENDING,
                "payment": PaymentStatus.UNPAID,
                "subtotal": Decimal("2499.00"),
                "total": Decimal("2499.00"),
                "note": "Repainting study room in warm beige shade.",
                "history": [
                    (BookingStatus.PENDING, "New booking created, awaiting worker broadcast.", "customer"),
                ],
            },
            # 9. Cancelled Booking - Alex
            {
                "number": "BK-2026-1009",
                "customer": alex["user"],
                "worker": None,
                "service": services_dict["kitchen-deep-cleaning"],
                "package": packages_dict["kitchen-deep-cleaning:standard-package"],
                "address": alex["address"],
                "date": today - timedelta(days=8),
                "start": time(11, 0),
                "end": time(13, 0),
                "status": BookingStatus.CANCELLED,
                "payment": PaymentStatus.REFUNDED,
                "subtotal": Decimal("699.00"),
                "total": Decimal("699.00"),
                "note": "Customer travel plans changed.",
                "history": [
                    (BookingStatus.PENDING, "Booking submitted.", "customer"),
                    (BookingStatus.CANCELLED, "Cancelled by customer: Travelling out of town.", "customer"),
                ],
            },
            # 10. Completed Bathroom Cleaning - Sarah & Nisha
            {
                "number": "BK-2026-1010",
                "customer": sarah["user"],
                "worker": nisha["user"],
                "service": services_dict["womens-salon-package"],
                "package": packages_dict["womens-salon-package:standard-package"],
                "address": sarah["address"],
                "date": today - timedelta(days=12),
                "start": time(14, 0),
                "end": time(16, 0),
                "status": BookingStatus.COMPLETED,
                "payment": PaymentStatus.PAID,
                "subtotal": Decimal("799.00"),
                "total": Decimal("799.00"),
                "note": "Doorbell not working, please call on mobile.",
                "history": [
                    (BookingStatus.PENDING, "Booking confirmed.", "customer"),
                    (BookingStatus.COMPLETED, "Spa session completed.", "worker"),
                ],
                "review": {
                    "rating": 5,
                    "comment": "Super relaxing session! Nisha used premium products and was very gentle.",
                    "reply": "Thank you so much Sarah! Looking forward to serving you again.",
                },
            },
        ]

        seeded_reviews_list = []
        for b_cfg in bookings_config:
            b_num = b_cfg["number"]
            booking, _ = Booking.objects.update_or_create(
                booking_number=b_num,
                defaults={
                    "customer": b_cfg["customer"],
                    "worker": b_cfg["worker"],
                    "service": b_cfg["service"],
                    "package": b_cfg["package"],
                    "package_price": b_cfg["package"].price,
                    "address": b_cfg["address"],
                    "booking_date": b_cfg["date"],
                    "start_time": b_cfg["start"],
                    "end_time": b_cfg["end"],
                    "estimated_duration": b_cfg["package"].duration,
                    "status": b_cfg["status"],
                    "payment_status": b_cfg["payment"],
                    "subtotal": b_cfg["subtotal"],
                    "total_amount": b_cfg["total"],
                    "customer_note": b_cfg["note"],
                    "is_reviewed": bool(b_cfg.get("review")),
                },
            )
            stats["bookings"] += 1

            # Status History
            for st, note, src in b_cfg["history"]:
                BookingStatusHistory.objects.get_or_create(
                    booking=booking,
                    status=st,
                    defaults={
                        "note": note,
                        "source": src,
                        "changed_by": b_cfg["worker"] if src == "worker" else b_cfg["customer"],
                    },
                )
                stats["booking_history"] += 1

            # Reviews
            if b_cfg.get("review") and booking.status == BookingStatus.COMPLETED:
                r_data = b_cfg["review"]
                review, _ = Review.objects.update_or_create(
                    booking=booking,
                    defaults={
                        "customer": b_cfg["customer"],
                        "service": b_cfg["service"],
                        "worker": b_cfg["worker"],
                        "rating": r_data["rating"],
                        "comment": r_data["comment"],
                    },
                )
                seeded_reviews_list.append(review)
                stats["reviews"] += 1

                # Review Reply
                if r_data.get("reply") and b_cfg["worker"]:
                    ReviewReply.objects.update_or_create(
                        review=review,
                        defaults={
                            "professional": b_cfg["worker"],
                            "comment": r_data["reply"],
                        },
                    )
                    stats["review_replies"] += 1

                # Review Report (if configured)
                if b_cfg.get("report"):
                    rep_cfg = b_cfg["report"]
                    ReviewReport.objects.update_or_create(
                        review=review,
                        reporter=arjun["user"],
                        defaults={
                            "reason": rep_cfg["reason"],
                            "description": rep_cfg["desc"],
                            "status": ReportStatus.PENDING,
                        },
                    )
                    stats["review_reports"] += 1

            # Seed Booking OTP (Phase 5)
            if b_cfg["number"] == "BK-2026-1006":
                # In-progress booking: OTP was verified
                BookingOTP.objects.update_or_create(
                    booking=booking,
                    defaults={
                        "otp_hash": make_password("482915"),
                        "expires_at": timezone.now() + timedelta(hours=2),
                        "is_verified": True,
                        "verified_at": timezone.now() - timedelta(hours=1),
                        "attempts": 0,
                        "max_attempts": 3,
                    },
                )
                stats["booking_otps"] += 1
            elif b_cfg["number"] == "BK-2026-1007":
                # Assigned/Arrived booking: OTP generated and active
                BookingOTP.objects.update_or_create(
                    booking=booking,
                    defaults={
                        "otp_hash": make_password("619340"),
                        "expires_at": timezone.now() + timedelta(minutes=15),
                        "is_verified": False,
                        "verified_at": None,
                        "attempts": 0,
                        "max_attempts": 3,
                    },
                )
                stats["booking_otps"] += 1

            # Seed Reschedule Requests (Phase 5)
            if b_cfg["number"] == "BK-2026-1007":
                # Pending reschedule request
                BookingRescheduleRequest.objects.update_or_create(
                    booking=booking,
                    requested_by=sarah["user"],
                    defaults={
                        "original_date": b_cfg["date"],
                        "original_start_time": b_cfg["start"],
                        "original_end_time": b_cfg["end"],
                        "requested_date": today + timedelta(days=3),
                        "requested_start_time": time(16, 0),
                        "requested_end_time": time(17, 30),
                        "reason": "Family visiting from out of town, requested schedule moved by 2 days.",
                        "status": RescheduleStatus.PENDING,
                    },
                )
                stats["booking_reschedule_requests"] += 1
            elif b_cfg["number"] == "BK-2026-1001":
                # Accepted historical reschedule request
                BookingRescheduleRequest.objects.update_or_create(
                    booking=booking,
                    requested_by=alex["user"],
                    defaults={
                        "original_date": b_cfg["date"] - timedelta(days=1),
                        "original_start_time": time(14, 0),
                        "original_end_time": time(18, 0),
                        "requested_date": b_cfg["date"],
                        "requested_start_time": b_cfg["start"],
                        "requested_end_time": b_cfg["end"],
                        "reason": "Shifted from afternoon to morning slot due to building maintenance.",
                        "status": RescheduleStatus.ACCEPTED,
                        "responded_by": rahul["user"],
                        "response_note": "Morning slot confirmed.",
                        "responded_at": timezone.now() - timedelta(days=14),
                    },
                )
                stats["booking_reschedule_requests"] += 1

        # --------------------------------------------------
        # STEP 9: RECALCULATE SERVICE & PRO RATINGS FROM REVIEWS
        # --------------------------------------------------
        self.stdout.write("-> Recalculating mathematical review averages...")
        for s_obj in services_dict.values():
            s_stats = Review.objects.filter(service=s_obj).aggregate(
                avg_r=Avg("rating"),
                count_r=Count("id"),
            )
            s_obj.average_rating = Decimal(f"{s_stats['avg_r'] or 4.90:.2f}")
            s_obj.reviews_count = s_stats["count_r"] or 15
            s_obj.save(update_fields=["average_rating", "reviews_count"])

        for w_obj in workers_dict.values():
            p_prof = w_obj["profile"]
            w_stats = Review.objects.filter(worker=p_prof.user).aggregate(
                avg_r=Avg("rating"),
                count_r=Count("id"),
            )
            p_prof.average_rating = Decimal(f"{w_stats['avg_r'] or 4.90:.2f}")
            p_prof.reviews_count = w_stats["count_r"] or 20
            p_prof.save(update_fields=["average_rating", "reviews_count"])

        # --------------------------------------------------
        # STEP 10: CUSTOMER COMPLAINTS (3 Demo Complaints)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Complaints...")
        complaints_data = [
            {
                "complaint_number": "CMP-2026-001",
                "customer": alex["user"],
                "booking": Booking.objects.filter(booking_number="BK-2026-1003").first(),
                "professional": ameen["user"],
                "category": ComplaintCategory.BILLING,
                "subject": "Inquiry regarding extra spare part invoice",
                "description": "I would like clarification regarding the additional washer cost mentioned during the tap repair.",
                "status": ComplaintStatus.UNDER_INVESTIGATION,
                "priority": ComplaintPriority.MEDIUM,
                "admin_notes": "Admin contacted customer and verified spare part MRP with professional.",
            },
            {
                "complaint_number": "CMP-2026-002",
                "customer": sarah["user"],
                "booking": Booking.objects.filter(booking_number="BK-2026-1002").first(),
                "professional": jithin["user"],
                "category": ComplaintCategory.SERVICE_QUALITY,
                "subject": "Minor water drop around indoor AC casing",
                "description": "Noticed minor condensation drip a few hours after service. Technician promptly guided me on drain alignment.",
                "status": ComplaintStatus.RESOLVED,
                "priority": ComplaintPriority.LOW,
                "resolution": "Technician revisited and adjusted the drain pipe gradient free of charge.",
                "resolved_by": admin_user,
                "resolved_at": now - timedelta(days=8),
            },
            {
                "complaint_number": "CMP-2026-003",
                "customer": arjun["user"],
                "booking": None,
                "professional": None,
                "category": ComplaintCategory.OTHER,
                "subject": "Request for specialized exterior painting in Calicut",
                "description": "Looking for commercial building exterior waterproofing options.",
                "status": ComplaintStatus.PENDING,
                "priority": ComplaintPriority.LOW,
                "admin_notes": "Forwarded to Calicut operations manager.",
            },
        ]

        for cmp_data in complaints_data:
            c_num = cmp_data.pop("complaint_number")
            Complaint.objects.update_or_create(
                complaint_number=c_num,
                defaults=cmp_data,
            )
            stats["complaints"] += 1

        # --------------------------------------------------
        # STEP 11: NOTIFICATIONS
        # --------------------------------------------------
        self.stdout.write("-> Seeding In-App Notifications...")
        notifications_data = [
            (alex["user"], NotificationType.BOOKING, "Booking Confirmed", "Your Home Deep Cleaning service is scheduled for tomorrow."),
            (alex["user"], NotificationType.REVIEW, "Review Submitted", "Thank you for reviewing Rahul Menon!"),
            (sarah["user"], NotificationType.BOOKING, "Professional Assigned", "Ameen Rahman has been assigned to your drain cleaning request."),
            (rahul["user"], NotificationType.BOOKING, "New Job Assigned", "You have been assigned to Booking BK-2026-1001."),
            (rahul["user"], NotificationType.REVIEW, "New 5-Star Review", "Alex Mathew left a 5-star review on your electrical repair work!"),
            (admin_user, NotificationType.VERIFICATION, "New KYC Verification", "Vikram Das submitted documents for painting specialist verification."),
            (admin_user, NotificationType.SYSTEM, "Platform Summary", "LocalHub weekly dispatch operating at 99.4% satisfaction rate."),
        ]

        for u, n_type, title, msg in notifications_data:
            Notification.objects.get_or_create(
                user=u,
                title=title,
                defaults={
                    "notification_type": n_type,
                    "message": msg,
                    "is_read": False,
                },
            )
            stats["notifications"] += 1

        # --------------------------------------------------
        # STEP 12: FAVOURITES
        # --------------------------------------------------
        self.stdout.write("-> Seeding Customer Favourites...")
        FavouriteService.objects.get_or_create(
            user=alex["user"],
            service=services_dict["home-deep-cleaning"],
        )
        FavouriteService.objects.get_or_create(
            user=sarah["user"],
            service=services_dict["ac-general-service"],
        )
        FavouriteProfessional.objects.get_or_create(
            user=alex["user"],
            professional=rahul["profile"],
        )
        stats["favourites"] += 3

        # --------------------------------------------------
        # STEP 13: TASK MARKETPLACE (Phase 4)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Task Marketplace Categories & Tasks...")
        task_categories_data = [
            {
                "name": "Home Maintenance & Repairs",
                "slug": "home-repairs",
                "description": "General carpentry, plumbing fixes, fixture mounting, and minor home repairs.",
                "icon_class": "lucide-wrench",
                "theme_color": "#F59E0B",
                "display_order": 1,
            },
            {
                "name": "Furniture Assembly & Setup",
                "slug": "furniture-assembly",
                "description": "Flat-pack wardrobe, desk, bed frame, shelf, and modular furniture assembly.",
                "icon_class": "lucide-box",
                "theme_color": "#6366F1",
                "display_order": 2,
            },
            {
                "name": "Electrical & Wiring",
                "slug": "electrical-wiring",
                "description": "Custom lighting, appliance installation, switchboard upgrades, and wiring.",
                "icon_class": "lucide-zap",
                "theme_color": "#EAB308",
                "display_order": 3,
            },
            {
                "name": "Interior Painting & Touch-ups",
                "slug": "painting-decor",
                "description": "Accent wall painting, patch repairs, door polishing, and wallpapering.",
                "icon_class": "lucide-paint-brush",
                "theme_color": "#EC4899",
                "display_order": 4,
            },
            {
                "name": "Moving & Heavy Lifting",
                "slug": "moving-lifting",
                "description": "Moving furniture between rooms, loading/unloading boxes, and bulky item transport.",
                "icon_class": "lucide-truck",
                "theme_color": "#10B981",
                "display_order": 5,
            },
            {
                "name": "Yard & Outdoor Work",
                "slug": "outdoor-yard",
                "description": "Garden cleanup, pressure washing driveway, balcony setup, and trimming.",
                "icon_class": "lucide-tree-deciduous",
                "theme_color": "#14B8A6",
                "display_order": 6,
            },
        ]

        task_cats_dict = {}
        for cat_d in task_categories_data:
            cat_obj, _ = TaskCategory.objects.update_or_create(
                slug=cat_d["slug"],
                defaults=cat_d,
            )
            task_cats_dict[cat_d["slug"]] = cat_obj
            stats["task_categories"] += 1

        vikram = workers_dict["vikram.painter@localhub.com"]

        tasks_config = [
            {
                "task_number": "TSK-2026-1001",
                "customer": alex["user"],
                "category": task_cats_dict["furniture-assembly"],
                "title": "Assemble IKEA 3-Door Wardrobe & Queen Bed Frame",
                "description": "Need an experienced hand to assemble a brand new IKEA 3-door wardrobe with mirrors and a wooden queen storage bed frame. All boxes and hardware manuals are on site in the master bedroom.",
                "budget": Decimal("1500.00"),
                "address": alex["address"],
                "house_name": "Flat 4B, Skyridge Heights",
                "area": "Kakkanad",
                "city": "Kochi",
                "postal_code": "682030",
                "preferred_date": today + timedelta(days=2),
                "preferred_time": time(10, 0),
                "status": TaskStatus.OPEN,
                "history": [
                    (TaskStatus.DRAFT, "Task created as draft.", "customer", alex["user"]),
                    (TaskStatus.OPEN, "Task published to marketplace.", "customer", alex["user"]),
                ],
                "applications": [
                    {
                        "professional": rahul["user"],
                        "proposed_price": Decimal("1400.00"),
                        "proposal": "I have professional drill kits and assemble IKEA flat-packs regularly. Can complete both items cleanly in under 3 hours.",
                        "estimated_duration": "3 hours",
                        "status": ApplicationStatus.PENDING,
                    },
                    {
                        "professional": ameen["user"],
                        "proposed_price": Decimal("1350.00"),
                        "proposal": "Available on your preferred date morning with all required alignment tools.",
                        "estimated_duration": "2.5 hours",
                        "status": ApplicationStatus.PENDING,
                    },
                ],
            },
            {
                "task_number": "TSK-2026-1002",
                "customer": sarah["user"],
                "category": task_cats_dict["electrical-wiring"],
                "title": "Mount 65-inch Smart TV & Conceal Cables in Living Room",
                "description": "Mount new 65-inch OLED TV to concrete wall in living room. Heavy-duty tilting wall mount bracket is already purchased. Need neat PVC casing or in-wall cable channeling for power and 2 HDMI cords.",
                "budget": Decimal("1200.00"),
                "address": sarah["address"],
                "house_name": "Villa 12, Palm Meadows",
                "area": "Palarivattom",
                "city": "Kochi",
                "postal_code": "682025",
                "preferred_date": today + timedelta(days=1),
                "preferred_time": time(14, 30),
                "status": TaskStatus.ASSIGNED,
                "assigned_professional": rahul["user"],
                "history": [
                    (TaskStatus.DRAFT, "Task created as draft.", "customer", sarah["user"]),
                    (TaskStatus.OPEN, "Task published to marketplace.", "customer", sarah["user"]),
                    (TaskStatus.ASSIGNED, "Rahul Menon selected as assigned professional.", "customer", sarah["user"]),
                ],
                "applications": [
                    {
                        "professional": rahul["user"],
                        "proposed_price": Decimal("1150.00"),
                        "proposal": "Certified electrician with stud finders, spirit levels, and hammer drill. Will ensure zero visible cables.",
                        "estimated_duration": "2 hours",
                        "status": ApplicationStatus.ACCEPTED,
                    },
                    {
                        "professional": ameen["user"],
                        "proposed_price": Decimal("1300.00"),
                        "proposal": "Can mount the TV securely on concrete wall with anchor bolts.",
                        "estimated_duration": "2 hours",
                        "status": ApplicationStatus.REJECTED,
                    },
                ],
            },
            {
                "task_number": "TSK-2026-1003",
                "customer": arjun["user"],
                "category": task_cats_dict["home-repairs"],
                "title": "Fix Leaking Kitchen Sink Pipe & Replace Dual Flow Valve",
                "description": "Constant water seepage underneath modular kitchen sink cabinet. Need to inspect CPVC drainage coupling and replace angle cock valve.",
                "budget": Decimal("900.00"),
                "address": arjun["address"],
                "house_name": "Royal Arcade #302",
                "area": "Kallai Road",
                "city": "Calicut",
                "postal_code": "673003",
                "preferred_date": today,
                "preferred_time": time(11, 0),
                "status": TaskStatus.IN_PROGRESS,
                "assigned_professional": ameen["user"],
                "history": [
                    (TaskStatus.DRAFT, "Task created as draft.", "customer", arjun["user"]),
                    (TaskStatus.OPEN, "Task published to marketplace.", "customer", arjun["user"]),
                    (TaskStatus.ASSIGNED, "Ameen Rahman selected as assigned professional.", "customer", arjun["user"]),
                    (TaskStatus.IN_PROGRESS, "Professional arrived and commenced work.", "professional", ameen["user"]),
                ],
                "applications": [
                    {
                        "professional": ameen["user"],
                        "proposed_price": Decimal("850.00"),
                        "proposal": "Plumbing specialist in Calicut with replacement CPVC seals and brass valves in toolkit.",
                        "estimated_duration": "1.5 hours",
                        "status": ApplicationStatus.ACCEPTED,
                    },
                ],
            },
            {
                "task_number": "TSK-2026-1004",
                "customer": alex["user"],
                "category": task_cats_dict["painting-decor"],
                "title": "Repaint Master Bedroom Accent Wall (Navy Blue Satin Finish)",
                "description": "Accent wall dimensions: 14ft x 10ft. Wall has minor pinholes from photo frames that require putty filling and 2 coats of Asian Paints Royal Satin.",
                "budget": Decimal("3500.00"),
                "address": alex["address"],
                "house_name": "Flat 4B, Skyridge Heights",
                "area": "Kakkanad",
                "city": "Kochi",
                "postal_code": "682030",
                "preferred_date": today - timedelta(days=5),
                "preferred_time": time(9, 0),
                "status": TaskStatus.COMPLETED,
                "assigned_professional": vikram["user"],
                "completed_at": timezone.now() - timedelta(days=4),
                "history": [
                    (TaskStatus.DRAFT, "Task created as draft.", "customer", alex["user"]),
                    (TaskStatus.OPEN, "Task published to marketplace.", "customer", alex["user"]),
                    (TaskStatus.ASSIGNED, "Vikram Das selected as assigned professional.", "customer", alex["user"]),
                    (TaskStatus.IN_PROGRESS, "Surface prep and painting started.", "professional", vikram["user"]),
                    (TaskStatus.COMPLETED, "Accent wall painting completed with customer sign-off.", "professional", vikram["user"]),
                ],
                "applications": [
                    {
                        "professional": vikram["user"],
                        "proposed_price": Decimal("3400.00"),
                        "proposal": "Professional painting contractor with masking tapes, roller sets, and sanding tools. Premium satin finish guaranteed.",
                        "estimated_duration": "5 hours",
                        "status": ApplicationStatus.ACCEPTED,
                    },
                ],
            },
            {
                "task_number": "TSK-2026-1005",
                "customer": sarah["user"],
                "category": task_cats_dict["moving-lifting"],
                "title": "Heavy Lifting: Move Teak Dining Table & Bookshelf to 2nd Floor",
                "description": "Need 2 strong individuals or a pro helper with moving straps to relocate a 6-seater solid teak wood dining table and 1 tall bookshelf from ground floor living room to 2nd floor study.",
                "budget": Decimal("1800.00"),
                "address": sarah["address"],
                "house_name": "Villa 12, Palm Meadows",
                "area": "Palarivattom",
                "city": "Kochi",
                "postal_code": "682025",
                "preferred_date": today + timedelta(days=4),
                "preferred_time": time(15, 0),
                "status": TaskStatus.OPEN,
                "history": [
                    (TaskStatus.DRAFT, "Task created as draft.", "customer", sarah["user"]),
                    (TaskStatus.OPEN, "Task published to marketplace.", "customer", sarah["user"]),
                ],
                "applications": [],
            },
            {
                "task_number": "TSK-2026-1006",
                "customer": arjun["user"],
                "category": task_cats_dict["electrical-wiring"],
                "title": "Install 3 High-Speed Ceiling Fans in New Apartment",
                "description": "Ceiling fan points are wired and tested. Just need assembly and mounting of 3 Atomberg BLDC ceiling fans with remote pairing.",
                "budget": Decimal("1200.00"),
                "address": arjun["address"],
                "house_name": "Royal Arcade #302",
                "area": "Kallai Road",
                "city": "Calicut",
                "postal_code": "673003",
                "preferred_date": today - timedelta(days=2),
                "preferred_time": time(16, 0),
                "status": TaskStatus.CANCELLED,
                "cancelled_at": timezone.now() - timedelta(days=2),
                "cancellation_reason": "Purchased pre-installed fan package from builder directly.",
                "history": [
                    (TaskStatus.DRAFT, "Task created as draft.", "customer", arjun["user"]),
                    (TaskStatus.OPEN, "Task published to marketplace.", "customer", arjun["user"]),
                    (TaskStatus.CANCELLED, "Cancelled by customer: Purchased pre-installed fan package from builder directly.", "customer", arjun["user"]),
                ],
                "applications": [],
            },
        ]

        for t_cfg in tasks_config:
            t_num = t_cfg["task_number"]
            hist_list = t_cfg.pop("history", [])
            apps_list = t_cfg.pop("applications", [])
            assigned_pro = t_cfg.pop("assigned_professional", None)
            comp_at = t_cfg.pop("completed_at", None)
            canc_at = t_cfg.pop("cancelled_at", None)
            canc_reason = t_cfg.pop("cancellation_reason", "")

            task_obj, _ = Task.objects.update_or_create(
                task_number=t_num,
                defaults={
                    **t_cfg,
                    "assigned_professional": assigned_pro,
                    "completed_at": comp_at,
                    "cancelled_at": canc_at,
                    "cancellation_reason": canc_reason,
                    "is_active": True,
                },
            )
            stats["tasks"] += 1

            # Seed Applications
            accepted_app_obj = None
            for app_d in apps_list:
                app_obj, _ = TaskApplication.objects.update_or_create(
                    task=task_obj,
                    professional=app_d["professional"],
                    defaults={
                        "proposed_price": app_d["proposed_price"],
                        "proposal": app_d["proposal"],
                        "estimated_duration": app_d["estimated_duration"],
                        "status": app_d["status"],
                    },
                )
                if app_d["status"] == ApplicationStatus.ACCEPTED:
                    accepted_app_obj = app_obj
                stats["task_applications"] += 1

            if accepted_app_obj:
                task_obj.accepted_application = accepted_app_obj
                task_obj.save(update_fields=["accepted_application"])

            # Seed Status History
            for st, note, src, user_obj in hist_list:
                TaskStatusHistory.objects.get_or_create(
                    task=task_obj,
                    status=st,
                    source=src,
                    changed_by=user_obj,
                    defaults={"note": note},
                )
                stats["task_status_history"] += 1

        # --------------------------------------------------
        # STEP 14: HEALTHCARE ECOSYSTEM (Phase 6)
        # --------------------------------------------------
        self.stdout.write("-> Seeding Healthcare Ecosystem Profiles & Appointments...")
        
        # 14.1 Healthcare Professional Profiles
        dr_kavita_user = workers_dict["dr.kavita.doctor@localhub.com"]["user"]
        sister_mary_user = workers_dict["sister.mary.nurse@localhub.com"]["user"]
        rohit_physio_user = workers_dict["rohit.physio@localhub.com"]["user"]

        dr_kavita_pro = workers_dict["dr.kavita.doctor@localhub.com"]["profile"]
        sister_mary_pro = workers_dict["sister.mary.nurse@localhub.com"]["profile"]
        rohit_physio_pro = workers_dict["rohit.physio@localhub.com"]["profile"]

        hp_kavita, _ = HealthcareProfessionalProfile.objects.update_or_create(
            professional=dr_kavita_user,
            defaults={
                "clinical_specialty": ClinicalSpecialty.GENERAL_PHYSICIAN,
                "registration_number": "KMC-2015-88412",
                "registration_council": "Travancore-Cochin Medical Council",
                "medical_degree": "MBBS, MD General Medicine",
                "years_of_clinical_exp": 10,
                "is_license_verified": True,
                "verified_at": timezone.now() - timedelta(days=29),
            },
        )
        stats["healthcare_pro_profiles"] += 1

        hp_mary, _ = HealthcareProfessionalProfile.objects.update_or_create(
            professional=sister_mary_user,
            defaults={
                "clinical_specialty": ClinicalSpecialty.HOME_NURSE,
                "registration_number": "KNC-2017-45910",
                "registration_council": "Kerala Nurses and Midwives Council",
                "medical_degree": "B.Sc Nursing (Critical Care & BLS Certified)",
                "years_of_clinical_exp": 8,
                "is_license_verified": True,
                "verified_at": timezone.now() - timedelta(days=29),
            },
        )
        stats["healthcare_pro_profiles"] += 1

        hp_rohit, _ = HealthcareProfessionalProfile.objects.update_or_create(
            professional=rohit_physio_user,
            defaults={
                "clinical_specialty": ClinicalSpecialty.PHYSIOTHERAPIST,
                "registration_number": "IAP-2018-12903",
                "registration_council": "Indian Association of Physiotherapists",
                "medical_degree": "BPT, MPT (Musculoskeletal Rehabilitation)",
                "years_of_clinical_exp": 7,
                "is_license_verified": True,
                "verified_at": timezone.now() - timedelta(days=29),
            },
        )
        stats["healthcare_pro_profiles"] += 1

        # 14.2 Patient Medical Profiles & Emergency Contacts
        patient_alex = customers_dict["customer@localhub.com"]["user"]
        patient_sarah = customers_dict["sarah.customer@localhub.com"]["user"]

        p_prof_alex, _ = PatientMedicalProfile.objects.update_or_create(
            user=patient_alex,
            defaults={
                "gender": GenderChoices.MALE,
                "date_of_birth": date(1972, 11, 20),
                "blood_group": "B+",
                "chronic_conditions": "Type 2 Diabetes Mellitus, Essential Hypertension",
                "mobility_assistance": True,
                "special_accommodations": "Patient has had recent knee arthroscopy; needs ground-floor seating during examination.",
            },
        )
        stats["patient_profiles"] += 1

        contact_alex, _ = EmergencyContact.objects.update_or_create(
            patient=patient_alex,
            name="Deepa Mathew",
            defaults={
                "relationship": "Spouse",
                "phone_number": "+919876543211",
                "is_primary": True,
            },
        )
        stats["emergency_contacts"] += 1

        p_prof_sarah, _ = PatientMedicalProfile.objects.update_or_create(
            user=patient_sarah,
            defaults={
                "gender": GenderChoices.FEMALE,
                "date_of_birth": date(1988, 4, 15),
                "blood_group": "O+",
                "chronic_conditions": "Mild Bronchial Asthma, Allergic to Penicillin",
                "mobility_assistance": False,
                "special_accommodations": "",
            },
        )
        stats["patient_profiles"] += 1

        contact_sarah, _ = EmergencyContact.objects.update_or_create(
            patient=patient_sarah,
            name="David Miller",
            defaults={
                "relationship": "Spouse",
                "phone_number": "+919876543299",
                "is_primary": True,
            },
        )
        stats["emergency_contacts"] += 1

        # 14.3 Healthcare Bookings, Appointments, Instructions & Visit Notes
        doc_service = services_dict.get("doctor-home-consultation")
        doc_pkg = packages_dict.get("doctor-home-consultation:single-doctor-visit") or ServicePackage.objects.filter(service=doc_service).first()
        alex_address = customers_dict["customer@localhub.com"]["address"]

        if doc_service and doc_pkg:
            # Create completed doctor visit booking
            booking_doc, _ = Booking.objects.update_or_create(
                booking_number="BK-2026-HC01",
                defaults={
                    "customer": patient_alex,
                    "worker": dr_kavita_user,
                    "service": doc_service,
                    "package": doc_pkg,
                    "package_price": doc_pkg.price,
                    "address": alex_address,
                    "booking_date": today - timedelta(days=2),
                    "start_time": time(10, 0),
                    "end_time": time(10, 45),
                    "estimated_duration": doc_pkg.duration,
                    "subtotal": doc_pkg.price,
                    "total_amount": doc_pkg.price,
                    "status": BookingStatus.COMPLETED,
                    "payment_status": PaymentStatus.PAID,
                    "customer_note": "Doctor home visit for hypertension review.",
                },
            )
            stats["bookings"] += 1

            # Healthcare Appointment
            appt_doc, _ = HealthcareAppointment.objects.update_or_create(
                booking=booking_doc,
                defaults={
                    "patient_profile": p_prof_alex,
                    "emergency_contact": contact_alex,
                    "appointment_type": AppointmentType.DOCTOR_VISIT,
                    "symptoms": "Routine 3-month hypertensive checkup, morning dizziness and occasional lethargy.",
                    "accessibility_needs": "Elevator access available in apartment complex.",
                    "is_emergency": False,
                },
            )
            stats["healthcare_appointments"] += 1

            # Pre-visit instruction
            PatientInstruction.objects.update_or_create(
                appointment=appt_doc,
                title="Keep Recent Blood Reports & Prescriptions Handy",
                defaults={
                    "instruction_text": "Please keep your past 3 months' blood glucose logs and prescription slips readily available for Dr. Kavita.",
                    "requires_fasting": False,
                    "fasting_hours": None,
                    "is_acknowledged": True,
                    "acknowledged_at": timezone.now() - timedelta(days=3),
                },
            )
            stats["patient_instructions"] += 1

            # Medical Visit Note
            MedicalVisitNote.objects.update_or_create(
                appointment=appt_doc,
                defaults={
                    "author": dr_kavita_user,
                    "systolic_bp": 124,
                    "diastolic_bp": 82,
                    "heart_rate_bpm": 74,
                    "temperature_f": Decimal("98.4"),
                    "oxygen_saturation": 99,
                    "clinical_observations": "Patient is alert, oriented, well-hydrated. Heart sounds normal S1/S2 heard, lungs clear bilaterally. No pedal edema. Surgical knee scar well healed.",
                    "care_recommendations": "Continue Amlodipine 5mg OD morning and Metformin 500mg BD after meals. Maintain low sodium diet, 30 min daily brisk walking. Review in 3 months.",
                },
            )
            stats["medical_visit_notes"] += 1

        nurse_service = services_dict.get("post-operative-home-nursing")
        nurse_pkg = packages_dict.get("post-operative-home-nursing:single-nursing-visit") or ServicePackage.objects.filter(service=nurse_service).first()
        sarah_address = customers_dict["sarah.customer@localhub.com"]["address"]

        if nurse_service and nurse_pkg:
            # Create confirmed upcoming nursing booking
            booking_nurse, _ = Booking.objects.update_or_create(
                booking_number="BK-2026-HC02",
                defaults={
                    "customer": patient_sarah,
                    "worker": sister_mary_user,
                    "service": nurse_service,
                    "package": nurse_pkg,
                    "package_price": nurse_pkg.price,
                    "address": sarah_address,
                    "booking_date": today + timedelta(days=1),
                    "start_time": time(11, 0),
                    "end_time": time(12, 0),
                    "estimated_duration": nurse_pkg.duration,
                    "subtotal": nurse_pkg.price,
                    "total_amount": nurse_pkg.price,
                    "status": BookingStatus.CONFIRMED,
                    "payment_status": PaymentStatus.UNPAID,
                    "customer_note": "Post-op surgical wound care.",
                },
            )
            stats["bookings"] += 1

            appt_nurse, _ = HealthcareAppointment.objects.update_or_create(
                booking=booking_nurse,
                defaults={
                    "patient_profile": p_prof_sarah,
                    "emergency_contact": contact_sarah,
                    "appointment_type": AppointmentType.NURSING,
                    "symptoms": "Post-laparoscopic sterile dressing change and wound inspection.",
                    "accessibility_needs": "Home visit on first floor (stairs).",
                    "is_emergency": False,
                },
            )
            stats["healthcare_appointments"] += 1

            PatientInstruction.objects.update_or_create(
                appointment=appt_nurse,
                title="Keep Surgical Discharge Summary Accessible",
                defaults={
                    "instruction_text": "Please keep hospital discharge notes and previous wound dressing instructions ready for Sister Mary.",
                    "requires_fasting": False,
                    "fasting_hours": None,
                    "is_acknowledged": False,
                    "acknowledged_at": None,
                },
            )
            stats["patient_instructions"] += 1

            # 14.4 Healthcare Organizations & Memberships
            self.stdout.write("-> Seeding Healthcare Organizations & Staff Memberships...")
            apollo_org, _ = HealthcareOrganization.objects.update_or_create(
                slug="apollo-homecare-clinic",
                defaults={
                    "name": "Apollo HomeCare Clinic",
                    "organization_type": OrganizationType.CLINIC,
                    "owner": dr_kavita_user,
                    "registration_number": "KL-MED-CLINIC-2024-8841",
                    "license_number": "DHS-KL-8841-B",
                    "contact_email": "contact@apollohomecare.demo",
                    "contact_phone": "+919876543201",
                    "address": "4th Cross, Panampilly Nagar",
                    "city": "Kochi",
                    "state": "Kerala",
                    "postal_code": "682036",
                    "description": "Multi-specialty primary care and home healthcare clinic providing physician visits, clinical nursing, and post-op rehabilitation.",
                    "is_verified": True,
                    "verification_status": "APPROVED",
                    "verified_at": timezone.now() - timedelta(days=60),
                    "is_active": True,
                    "average_rating": Decimal("4.95"),
                    "reviews_count": 48,
                },
            )
            apollo_org.services.set([s for s in [doc_service, nurse_service, services_dict.get("orthopedic-physiotherapy-session")] if s])
            stats["healthcare_organizations"] += 1

            # Organization Verification Document for Apollo
            OrganizationVerificationDocument.objects.update_or_create(
                organization=apollo_org,
                document_type="CLINICAL_LICENSE",
                defaults={
                    "document_number": "DHS-KL-8841-B",
                    "status": DocumentStatus.VERIFIED,
                    "reviewed_at": timezone.now() - timedelta(days=60),
                },
            )
            stats["organization_documents"] += 1

            # Staff memberships in Apollo
            OrganizationMembership.objects.update_or_create(
                organization=apollo_org,
                user=dr_kavita_user,
                defaults={
                    "role": OrganizationRole.DOCTOR,
                    "is_active": True,
                },
            )
            stats["organization_memberships"] += 1

            OrganizationMembership.objects.update_or_create(
                organization=apollo_org,
                user=sister_mary_user,
                defaults={
                    "role": OrganizationRole.NURSE,
                    "is_active": True,
                },
            )
            stats["organization_memberships"] += 1

            OrganizationMembership.objects.update_or_create(
                organization=apollo_org,
                user=rohit_physio_user,
                defaults={
                    "role": OrganizationRole.STAFF,
                    "is_active": True,
                },
            )
            stats["organization_memberships"] += 1

            # CareFirst Diagnostic Centre
            carefirst_org, _ = HealthcareOrganization.objects.update_or_create(
                slug="carefirst-diagnostic-labs",
                defaults={
                    "name": "CareFirst Diagnostic Labs",
                    "organization_type": OrganizationType.DIAGNOSTIC_CENTRE,
                    "owner": admin_user,
                    "registration_number": "NABL-LAB-KL-2023-1102",
                    "license_number": "LAB-LIC-9902",
                    "contact_email": "labs@carefirst.demo",
                    "contact_phone": "+919876543202",
                    "address": "MG Road, Marine Drive",
                    "city": "Kochi",
                    "state": "Kerala",
                    "postal_code": "682011",
                    "description": "NABL-accredited diagnostic laboratory providing automated doorstep blood sampling, pathology, and wellness test packages.",
                    "is_verified": True,
                    "verification_status": "APPROVED",
                    "verified_at": timezone.now() - timedelta(days=45),
                    "is_active": True,
                    "average_rating": Decimal("4.88"),
                    "reviews_count": 92,
                },
            )
            if services_dict.get("full-body-health-checkup-lab"):
                carefirst_org.services.set([services_dict["full-body-health-checkup-lab"]])
            stats["healthcare_organizations"] += 1

            # Link doctor appointment to Apollo HomeCare Clinic
            if 'appt_doc' in locals():
                appt_doc.organization = apollo_org
                appt_doc.save(update_fields=["organization"])

            # --------------------------------------------------
            # STEP 13: PAYMENTS & FINANCIAL ECOSYSTEM (Phase 7)
            # --------------------------------------------------
            self.stdout.write("-> Seeding Payments & Financial Ecosystem (Wallets, Invoices, Promo, Escrow, Payouts)...")

            # 1. Promo Codes
            promos_data = [
                {
                    "code": "WELCOME50",
                    "description": "50% instant discount on your first home service (up to ₹200)",
                    "discount_type": PromoDiscountType.PERCENTAGE,
                    "discount_value": Decimal("50.00"),
                    "max_discount_amount": Decimal("200.00"),
                    "min_order_amount": Decimal("299.00"),
                    "valid_from": timezone.now() - timedelta(days=30),
                    "valid_until": timezone.now() + timedelta(days=90),
                    "usage_limit": 500,
                    "used_count": 14,
                    "is_active": True,
                },
                {
                    "code": "LOCAL100",
                    "description": "Flat ₹100 discount on bookings above ₹500",
                    "discount_type": PromoDiscountType.FIXED,
                    "discount_value": Decimal("100.00"),
                    "max_discount_amount": None,
                    "min_order_amount": Decimal("500.00"),
                    "valid_from": timezone.now() - timedelta(days=15),
                    "valid_until": timezone.now() + timedelta(days=60),
                    "usage_limit": 200,
                    "used_count": 8,
                    "is_active": True,
                },
                {
                    "code": "FESTIVE20",
                    "description": "20% off all appliance and cleaning services",
                    "discount_type": PromoDiscountType.PERCENTAGE,
                    "discount_value": Decimal("20.00"),
                    "max_discount_amount": Decimal("300.00"),
                    "min_order_amount": Decimal("400.00"),
                    "valid_from": timezone.now() - timedelta(days=5),
                    "valid_until": timezone.now() + timedelta(days=45),
                    "usage_limit": 1000,
                    "used_count": 22,
                    "is_active": True,
                },
            ]
            for p_dict in promos_data:
                promo_obj, created = PromoCode.objects.update_or_create(
                    code=p_dict["code"],
                    defaults=p_dict,
                )
                if created:
                    stats["promo_codes"] += 1

            welcome_promo = PromoCode.objects.get(code="WELCOME50")

            # 2. Seed Wallets & Transactions
            all_users = User.objects.filter(email__in=self.ALL_SEED_EMAILS)
            for u in all_users:
                initial_bal = Decimal("2500.00") if u.role == User.Role.CUSTOMER else (Decimal("8450.00") if u.role == User.Role.PROFESSIONAL else Decimal("0.00"))
                w = Wallet.objects.filter(user=u).first()
                if not w:
                    w = Wallet.objects.create(user=u, current_balance=initial_bal, currency="INR")
                else:
                    w.current_balance = initial_bal
                    w.pending_balance = Decimal("0.00")
                    w.save(update_fields=["current_balance", "pending_balance"])
                stats["wallets"] += 1

                if initial_bal > Decimal("0.00") and not w.transactions.exists():
                    WalletTransaction.objects.create(
                        wallet=w,
                        transaction_type=TransactionType.WALLET_TOPUP if u.role == User.Role.CUSTOMER else TransactionType.EARNING_CREDIT,
                        amount=initial_bal,
                        balance_after=initial_bal,
                        reference_id=f"INIT-{u.email[:6].upper()}",
                        description="Initial verified balance credit",
                    )
                    stats["wallet_transactions"] += 1

            # 3. Seed Payments, Invoices, Escrows & Commissions for Existing Bookings
            seed_bk_qs = Booking.objects.filter(booking_number__in=self.SEED_BOOKING_NUMBERS).select_related("customer", "worker", "service", "address")
            inv_idx = 1
            for b in seed_bk_qs:
                is_completed = b.status == BookingStatus.COMPLETED
                pay_method = PaymentMethod.ONLINE if inv_idx % 2 == 0 else PaymentMethod.WALLET
                pay_ref = f"PAY-2026-100{inv_idx:02d}"
                idemp_key = f"seed_idemp_bk_{b.booking_number}"

                subtotal = b.total_amount
                discount = Decimal("100.00") if inv_idx == 1 else Decimal("0.00")
                promo = welcome_promo if inv_idx == 1 else None
                total = max(Decimal("0.00"), subtotal - discount)

                payment_obj, p_created = Payment.objects.update_or_create(
                    payment_reference=pay_ref,
                    defaults={
                        "idempotency_key": idemp_key,
                        "customer": b.customer,
                        "booking": b,
                        "payment_method": pay_method,
                        "status": FinancialPaymentStatus.COMPLETED if is_completed or b.status in [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS] else FinancialPaymentStatus.PENDING,
                        "subtotal": subtotal,
                        "discount_amount": discount,
                        "promo_code": promo,
                        "platform_fee": Decimal("0.00"),
                        "total_amount": total,
                        "paid_at": timezone.now() - timedelta(days=2) if is_completed else timezone.now(),
                        "gateway_transaction_id": f"mock_gw_{pay_ref}",
                    },
                )
                if p_created:
                    stats["payments"] += 1

                # Update booking payment_status
                if payment_obj.status == FinancialPaymentStatus.COMPLETED:
                    b.payment_status = PaymentStatus.PAID
                    b.save(update_fields=["payment_status"])

                # Invoice
                inv_num = f"INV-2026-{1000 + inv_idx:05d}"
                inv_addr = f"{b.address.house_name}, {b.address.area}, {b.address.city}" if b.address else "Bangalore"
                svc_title = getattr(b.service, "name", getattr(b.service, "title", "Service"))
                inv_obj, i_created = Invoice.objects.update_or_create(
                    payment=payment_obj,
                    defaults={
                        "invoice_number": inv_num,
                        "customer": b.customer,
                        "recipient_name": b.customer.full_name or b.customer.email,
                        "recipient_email": b.customer.email,
                        "recipient_address": inv_addr,
                        "service_summary": f"{svc_title} ({b.booking_number})",
                        "subtotal": subtotal,
                        "discount": discount,
                        "platform_fee": Decimal("0.00"),
                        "tax": Decimal("0.00"),
                        "total_amount": total,
                        "status": InvoiceStatus.PAID if payment_obj.status == FinancialPaymentStatus.COMPLETED else InvoiceStatus.ISSUED,
                    },
                )
                if i_created:
                    stats["invoices"] += 1

                # Escrow & Commission
                if is_completed and b.worker:
                    escrow_obj, e_created = EscrowHold.objects.update_or_create(
                        payment=payment_obj,
                        defaults={
                            "booking": b,
                            "professional": b.worker,
                            "held_amount": total,
                            "status": EscrowStatus.RELEASED,
                            "released_at": timezone.now() - timedelta(days=1),
                            "release_reference": f"REL-{b.booking_number}",
                        },
                    )
                    if e_created:
                        stats["escrow_holds"] += 1

                    comm_amt = (total * Decimal("0.10")).quantize(Decimal("0.01"))
                    net_amt = total - comm_amt
                    comm_obj, c_created = CommissionRecord.objects.update_or_create(
                        payment=payment_obj,
                        defaults={
                            "booking": b,
                            "professional": b.worker,
                            "gross_amount": total,
                            "commission_rate_percentage": Decimal("10.00"),
                            "commission_amount": comm_amt,
                            "net_earning": net_amt,
                            "is_settled": True,
                            "settled_at": timezone.now() - timedelta(days=1),
                        },
                    )
                    if c_created:
                        stats["commission_records"] += 1
                elif b.status in [BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]:
                    escrow_obj, e_created = EscrowHold.objects.update_or_create(
                        payment=payment_obj,
                        defaults={
                            "booking": b,
                            "professional": b.worker,
                            "held_amount": total,
                            "status": EscrowStatus.HELD,
                        },
                    )
                    if e_created:
                        stats["escrow_holds"] += 1

                inv_idx += 1

            # 4. Seed Professional Payouts
            rahul_user = User.objects.filter(email="rahul.electrician@localhub.com").first()
            if rahul_user:
                po_completed, po_c_created = ProfessionalPayout.objects.update_or_create(
                    payout_reference="PO-2026-0001",
                    defaults={
                        "professional": rahul_user,
                        "amount": Decimal("3500.00"),
                        "payout_method": PayoutMethod.UPI,
                        "account_details": {"upi_id": "rahul.electrician@okhdfcbank"},
                        "status": PayoutStatus.COMPLETED,
                        "processed_at": timezone.now() - timedelta(days=3),
                        "admin_notes": "Monthly settlement transferred via UPI gateway.",
                    },
                )
                if po_c_created:
                    stats["payouts"] += 1

                po_pending, po_p_created = ProfessionalPayout.objects.update_or_create(
                    payout_reference="PO-2026-0002",
                    defaults={
                        "professional": rahul_user,
                        "amount": Decimal("1200.00"),
                        "payout_method": PayoutMethod.BANK_TRANSFER,
                        "account_details": {
                            "bank_name": "HDFC Bank",
                            "account_number": "XXXX-XXXX-4819",
                            "ifsc_code": "HDFC0001234",
                        },
                        "status": PayoutStatus.REQUESTED,
                    },
                )
                if po_p_created:
                    stats["payouts"] += 1

            # 5. Seed Refund Request
            demo_customer = User.objects.filter(email="customer@localhub.com").first()
            sample_payment = Payment.objects.filter(customer=demo_customer).first()
            if demo_customer and sample_payment:
                ref_obj, ref_created = RefundRequest.objects.update_or_create(
                    refund_reference="REF-2026-0001",
                    defaults={
                        "payment": sample_payment,
                        "customer": demo_customer,
                        "amount": sample_payment.total_amount,
                        "reason": "Service professional requested rescheduling due to emergency.",
                        "refund_method": RefundMethod.WALLET_CREDIT,
                        "status": RefundStatus.COMPLETED,
                        "reviewed_at": timezone.now() - timedelta(days=2),
                        "admin_notes": "Approved and credited to customer wallet.",
                    },
                )
                if ref_created:
                    stats["refund_requests"] += 1

        return stats

    def _print_summary(self, stats):
        self.stdout.write(self.style.SUCCESS("\nLocalHub seed completed successfully.\n"))
        self.stdout.write(self.style.MIGRATE_HEADING("Created / Updated Record Breakdown:"))
        for key, count in stats.items():
            formatted_key = key.replace("_", " ").title()
            self.stdout.write(f"  * {formatted_key:26}: {count}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("  LOCALHUB DEVELOPMENT LOGIN CREDENTIALS"))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(f"Common Password for all demo accounts: {self.DEV_PASSWORD}\n")

        self.stdout.write(self.style.SUCCESS("ADMIN ACCOUNT:"))
        self.stdout.write(f"  * Email: {self.SEED_ADMIN_EMAIL} (Full Administrative Access)")

        self.stdout.write(self.style.SUCCESS("\nCUSTOMER ACCOUNTS:"))
        for email in self.SEED_CUSTOMER_EMAILS:
            self.stdout.write(f"  * Email: {email}")

        self.stdout.write(self.style.SUCCESS("\nPROFESSIONAL / WORKER ACCOUNTS:"))
        for email in self.SEED_WORKER_EMAILS:
            status_note = "(Verified Pro)" if "vikram" not in email else "(Pending Verification)"
            self.stdout.write(f"  * Email: {email} {status_note}")
        self.stdout.write(self.style.MIGRATE_HEADING("==================================================\n"))
