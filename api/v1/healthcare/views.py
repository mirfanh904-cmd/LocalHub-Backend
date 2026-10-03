from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiResponse

from services.models import Service, ServiceGroup, Category
from accounts.models import Address, User, ProfessionalProfile
from healthcare.models import (
    PatientMedicalProfile,
    EmergencyContact,
    HealthcareProfessionalProfile,
    HealthcareOrganization,
    OrganizationMembership,
    HealthcareAppointment,
    PatientInstruction,
    MedicalVisitNote,
    OrganizationRole,
)
from healthcare.selectors import HealthcareSelector
from healthcare.services import (
    PatientProfileService,
    EmergencyContactService,
    HealthcareAppointmentService,
    MedicalVisitNoteService,
    HealthcareProfessionalService,
)
from healthcare.permissions import IsPatientOrAssignedHealthcareProvider
from .serializers import (
    HealthcareServiceSerializer,
    HealthcareProfessionalPublicSerializer,
    HealthcareOrganizationSerializer,
    OrganizationMembershipSerializer,
    PatientMedicalProfileSerializer,
    EmergencyContactSerializer,
    HealthcareProfessionalProfileSerializer,
    HealthcareAppointmentDetailSerializer,
    HealthcareBookingCreateSerializer,
    MedicalVisitNoteSerializer,
    MedicalVisitNoteCreateSerializer,
    PatientInstructionSerializer,
)


class HealthcareServiceListAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_healthcare_services",
        summary="List Healthcare Services",
        description="Public API listing all active specialized healthcare and clinical services with pricing, images, and packages.",
        responses={200: HealthcareServiceSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        services = Service.objects.filter(
            Q(category__service_group__slug__icontains="health") |
            Q(category__slug__icontains="health") |
            Q(category__slug__in=["doctor-home-visit", "home-nursing-care", "physiotherapy-rehab", "elderly-caregiving", "lab-sample-collection", "nursing-care"]) |
            Q(name__icontains="Doctor") |
            Q(name__icontains="Nurse") |
            Q(name__icontains="Physiotherapy") |
            Q(name__icontains="Elder") |
            Q(name__icontains="Lab"),
            is_active=True,
        ).select_related("category", "category__service_group").prefetch_related("packages").order_by("display_order", "name").distinct()

        # Query param filtering
        search_query = request.query_params.get("search")
        if search_query:
            services = services.filter(
                Q(name__icontains=search_query) |
                Q(short_description__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        ordering = request.query_params.get("ordering")
        if ordering:
            if ordering in ["starting_price", "-starting_price", "average_rating", "-average_rating", "name", "-name"]:
                services = services.order_by(ordering)

        category_param = request.query_params.get("category")
        if category_param and category_param != "all":
            services = services.filter(
                Q(category__slug=category_param) |
                Q(category__service_group__slug=category_param)
            )

        subcategory_param = request.query_params.get("subcategory")
        if subcategory_param and subcategory_param != "all":
            services = services.filter(
                Q(category__slug=subcategory_param) |
                Q(slug=subcategory_param)
            )

        serializer = HealthcareServiceSerializer(services, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class HealthcareCategoryListAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_healthcare_categories",
        summary="List Healthcare Categories & Groups",
        description="Public catalog listing specialized clinical and in-home healthcare categories.",
        responses={200: OpenApiResponse(description="Healthcare category catalog")},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        categories = Category.objects.filter(
            Q(service_group__slug__icontains="health") |
            Q(slug__icontains="health") |
            Q(slug__in=["doctor-home-visit", "home-nursing-care", "physiotherapy-rehab", "elderly-caregiving", "lab-sample-collection", "nursing-care"]),
            is_active=True,
        ).select_related("service_group").prefetch_related("services").order_by("display_order", "name").distinct()

        if not categories.exists():
            categories = Category.objects.filter(
                Q(services__name__icontains="Doctor") |
                Q(services__name__icontains="Nurse") |
                Q(services__name__icontains="Physiotherapy") |
                Q(services__name__icontains="Elder") |
                Q(services__name__icontains="Lab"),
                is_active=True,
            ).distinct().select_related("service_group").prefetch_related("services")

        categories_data = []
        for cat in categories:
            active_services = cat.services.filter(is_active=True).order_by("display_order", "name")
            services = [
                {
                    "id": s.id,
                    "name": s.name,
                    "slug": s.slug,
                    "starting_price": str(s.starting_price),
                    "short_description": s.short_description or s.description or "",
                    "cover_image": s.cover_image.url if s.cover_image else None,
                    "estimated_duration": s.estimated_duration,
                    "average_rating": str(s.average_rating),
                    "reviews_count": s.reviews_count,
                    "is_featured": s.is_featured,
                }
                for s in active_services
            ]

            cover_img = cat.cover_image.url if cat.cover_image else None
            if not cover_img:
                fallbacks = {
                    "doctor": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=800&q=85",
                    "nurs": "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?auto=format&fit=crop&w=800&q=85",
                    "physio": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=800&q=85",
                    "elder": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=800&q=85",
                    "lab": "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=800&q=85",
                }
                for key, url in fallbacks.items():
                    if key in cat.slug or key in cat.name.lower():
                        cover_img = url
                        break
                if not cover_img:
                    cover_img = "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&w=800&q=85"

            categories_data.append({
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "short_description": cat.short_description,
                "description": cat.description,
                "cover_image": cover_img,
                "service_group_name": cat.service_group.name if cat.service_group else "",
                "service_group_slug": cat.service_group.slug if cat.service_group else "",
                "services": services,
            })

        return Response({"success": True, "data": categories_data}, status=status.HTTP_200_OK)


class HealthcareProfessionalListPublicAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_public_healthcare_professionals",
        summary="List Verified Healthcare Professionals",
        description="Public API returning verified doctors, nurses, and clinical specialists available for home visits.",
        responses={200: HealthcareProfessionalPublicSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        specialty = request.query_params.get("specialty")
        queryset = HealthcareProfessionalProfile.objects.filter(
            is_license_verified=True,
        ).select_related("professional", "professional__professional_profile", "professional__profile")

        if specialty:
            queryset = queryset.filter(clinical_specialty=specialty)

        serializer = HealthcareProfessionalPublicSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class HealthcareOrganizationListPublicAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_public_healthcare_organizations",
        summary="List Verified Healthcare Organizations",
        description="Public API listing verified hospitals, clinics, diagnostic centers, and healthcare agencies.",
        responses={200: HealthcareOrganizationSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        org_type = request.query_params.get("type")
        queryset = HealthcareOrganization.objects.filter(
            is_verified=True,
        ).select_related("owner").prefetch_related("services", "memberships")

        if org_type:
            queryset = queryset.filter(organization_type=org_type)

        serializer = HealthcareOrganizationSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class HealthcareOrganizationDetailAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="get_healthcare_organization_detail",
        summary="Get Healthcare Organization Details",
        description="Returns detailed profile, services, and staff for a verified healthcare organization.",
        responses={200: HealthcareOrganizationSerializer},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request, slug_or_id):
        if str(slug_or_id).isdigit():
            org = get_object_or_404(HealthcareOrganization, id=int(slug_or_id))
        else:
            org = get_object_or_404(HealthcareOrganization, slug=slug_or_id)

        serializer = HealthcareOrganizationSerializer(org)
        staff = org.memberships.filter(is_active=True).select_related("user", "professional_profile")
        staff_serializer = OrganizationMembershipSerializer(staff, many=True)

        return Response({
            "success": True,
            "data": {
                **serializer.data,
                "staff_members": staff_serializer.data,
            }
        }, status=status.HTTP_200_OK)


class HealthcareOrganizationDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_organization_dashboard",
        summary="Organization Dashboard Overview",
        description="Retrieves administrative overview, appointments, staff list, and metrics for organization owner or staff.",
        responses={200: OpenApiResponse(description="Organization dashboard data")},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            is_active=True,
        ).select_related("organization").first()

        if not membership:
            # Check if user owns an organization
            org = HealthcareOrganization.objects.filter(owner=request.user).first()
            if not org:
                return Response(
                    {"success": False, "message": "No active organization associated with your account."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            org = membership.organization

        appointments = HealthcareAppointment.objects.filter(
            organization=org,
        ).select_related("booking", "booking__service", "booking__worker", "patient_profile")

        staff = org.memberships.filter(is_active=True).select_related("user")

        total_appointments = appointments.count()
        completed_appointments = appointments.filter(booking__status="COMPLETED").count()
        pending_appointments = appointments.filter(booking__status__in=["REQUESTED", "CONFIRMED", "IN_PROGRESS"]).count()

        return Response({
            "success": True,
            "data": {
                "organization": HealthcareOrganizationSerializer(org).data,
                "metrics": {
                    "total_appointments": total_appointments,
                    "completed_appointments": completed_appointments,
                    "pending_appointments": pending_appointments,
                    "total_staff": staff.count(),
                    "average_rating": str(org.average_rating),
                    "reviews_count": org.reviews_count,
                },
                "appointments": HealthcareAppointmentDetailSerializer(appointments[:20], many=True).data,
                "staff_members": OrganizationMembershipSerializer(staff, many=True).data,
            }
        }, status=status.HTTP_200_OK)


class HealthcareOrganizationStaffAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationMembershipSerializer

    @extend_schema(
        operation_id="manage_organization_staff_list",
        summary="List Organization Staff",
        description="Organization owner/admin can list and register healthcare practitioners into their organization.",
        responses={200: OrganizationMembershipSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        org = HealthcareOrganization.objects.filter(
            Q(owner=request.user) | Q(memberships__user=request.user, memberships__role=OrganizationRole.OWNER),
        ).first()

        if not org:
            return Response({"success": False, "message": "Organization not found or unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        members = org.memberships.filter(is_active=True).select_related("user", "professional_profile")
        return Response({"success": True, "data": OrganizationMembershipSerializer(members, many=True).data})

    @extend_schema(
        operation_id="manage_organization_staff_add",
        summary="Add Organization Staff",
        request=OrganizationMembershipSerializer,
        responses={200: OrganizationMembershipSerializer},
        tags=["Healthcare Ecosystem"],
    )
    def post(self, request):
        org = HealthcareOrganization.objects.filter(
            Q(owner=request.user) | Q(memberships__user=request.user, memberships__role=OrganizationRole.OWNER),
        ).first()

        if not org:
            return Response({"success": False, "message": "Organization not found or unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        email = request.data.get("email")
        role = request.data.get("role", OrganizationRole.STAFF)

        if not email:
            return Response({"success": False, "message": "Staff user email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user_obj = User.objects.filter(email=email).first()
        if not user_obj:
            return Response({"success": False, "message": f"User with email {email} is not registered on LocalHub."}, status=status.HTTP_404_NOT_FOUND)

        pro_profile = getattr(user_obj, "professional_profile", None)
        membership, created = OrganizationMembership.objects.get_or_create(
            organization=org,
            user=user_obj,
            defaults={
                "role": role,
                "professional_profile": pro_profile,
                "is_active": True,
            },
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.role = role
            membership.save()

        return Response({
            "success": True,
            "message": f"{user_obj.full_name or user_obj.email} added to organization staff.",
            "data": OrganizationMembershipSerializer(membership).data,
        }, status=status.HTTP_201_CREATED)


class PatientMedicalProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_patient_medical_profile",
        summary="Get Patient Medical Profile",
        description="Retrieves confidential medical history and clinical background for authenticated customer.",
        responses={200: PatientMedicalProfileSerializer},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        profile = HealthcareSelector.get_patient_profile(request.user)
        return Response({"success": True, "data": PatientMedicalProfileSerializer(profile).data})

    @extend_schema(
        operation_id="update_patient_medical_profile",
        summary="Update Patient Medical Profile",
        description="Creates or updates confidential medical history, allergies, and accommodations.",
        request=PatientMedicalProfileSerializer,
        responses={200: PatientMedicalProfileSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["Healthcare Ecosystem"],
    )
    def put(self, request):
        serializer = PatientMedicalProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile = PatientProfileService.update_profile(request.user, serializer.validated_data)
            return Response({
                "success": True,
                "message": "Patient medical profile updated successfully.",
                "data": PatientMedicalProfileSerializer(profile).data,
            }, status=status.HTTP_200_OK)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmergencyContactListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_emergency_contacts",
        summary="List Emergency Contacts",
        description="Retrieves patient emergency contacts for in-home care escalation.",
        responses={200: EmergencyContactSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        contacts = HealthcareSelector.list_emergency_contacts(request.user)
        return Response({"success": True, "data": EmergencyContactSerializer(contacts, many=True).data})

    @extend_schema(
        operation_id="create_emergency_contact",
        summary="Add Emergency Contact",
        description="Registers a new emergency contact for the authenticated user.",
        request=EmergencyContactSerializer,
        responses={201: EmergencyContactSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["Healthcare Ecosystem"],
    )
    def post(self, request):
        serializer = EmergencyContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            contact = EmergencyContactService.create_contact(request.user, serializer.validated_data)
            return Response({
                "success": True,
                "message": "Emergency contact added successfully.",
                "data": EmergencyContactSerializer(contact).data,
            }, status=status.HTTP_201_CREATED)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmergencyContactDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="delete_emergency_contact",
        summary="Delete Emergency Contact",
        description="Removes an emergency contact.",
        responses={200: OpenApiResponse(description="Contact removed")},
        tags=["Healthcare Ecosystem"],
    )
    def delete(self, request, pk):
        try:
            EmergencyContactService.delete_contact(request.user, pk)
            return Response({"success": True, "message": "Emergency contact removed."}, status=status.HTTP_200_OK)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HealthcareAppointmentBookAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="book_healthcare_appointment",
        summary="Book Specialized Healthcare Appointment",
        description="Creates a specialized in-home healthcare booking with patient clinical intake, emergency contacts, organization routing, and pre-visit prep instructions.",
        request=HealthcareBookingCreateSerializer,
        responses={201: HealthcareAppointmentDetailSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["Healthcare Ecosystem"],
    )
    def post(self, request):
        serializer = HealthcareBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        val_data = serializer.validated_data

        try:
            service_obj = get_object_or_404(Service, id=val_data["service"])
            address_obj = get_object_or_404(Address, id=val_data["address"], user=request.user)
            package_obj = None
            if val_data.get("package"):
                from services.models import ServicePackage
                package_obj = ServicePackage.objects.filter(id=val_data["package"]).first()

            worker_obj = None
            if val_data.get("worker"):
                worker_obj = User.objects.filter(id=val_data["worker"], role="PROFESSIONAL").first()

            org_obj = None
            if val_data.get("organization_id"):
                org_obj = HealthcareOrganization.objects.filter(id=val_data["organization_id"]).first()

            booking_payload = {
                "service": service_obj,
                "package": package_obj,
                "address": address_obj,
                "worker": worker_obj,
                "booking_date": val_data["booking_date"],
                "start_time": val_data["start_time"],
                "end_time": val_data["end_time"],
                "subtotal": val_data["subtotal"],
                "discount": val_data.get("discount", 0),
                "platform_fee": val_data.get("platform_fee", 0),
                "tax": val_data.get("tax", 0),
                "customer_note": val_data.get("customer_note", ""),
            }

            healthcare_payload = {
                "organization": org_obj,
                "appointment_type": val_data["appointment_type"],
                "symptoms": val_data.get("symptoms", ""),
                "accessibility_needs": val_data.get("accessibility_needs", ""),
                "pre_visit_instructions": val_data.get("pre_visit_instructions", ""),
                "emergency_contact_id": val_data.get("emergency_contact_id"),
                "is_emergency": val_data.get("is_emergency", False),
            }

            appointment = HealthcareAppointmentService.book_healthcare_appointment(
                customer=request.user,
                booking_payload=booking_payload,
                healthcare_payload=healthcare_payload,
            )

            return Response({
                "success": True,
                "message": "Healthcare appointment booked successfully.",
                "data": HealthcareAppointmentDetailSerializer(appointment).data,
            }, status=status.HTTP_201_CREATED)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HealthcareAppointmentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_healthcare_appointments",
        summary="List Healthcare Appointments",
        description="Lists all healthcare appointments for authenticated patient or assigned healthcare worker.",
        responses={200: HealthcareAppointmentDetailSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        appointments = HealthcareSelector.list_appointments_for_user(request.user)
        return Response({
            "success": True,
            "data": HealthcareAppointmentDetailSerializer(appointments, many=True).data,
        }, status=status.HTTP_200_OK)


class HealthcareAppointmentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPatientOrAssignedHealthcareProvider]

    @extend_schema(
        operation_id="get_healthcare_appointment_detail",
        summary="Get Healthcare Appointment Details",
        description="Retrieves confidential clinical appointment data, vital observations, and pre-visit instructions.",
        responses={200: HealthcareAppointmentDetailSerializer, 404: OpenApiResponse(description="Appointment not found")},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request, booking_number):
        appointment = HealthcareSelector.get_appointment_by_booking_number(booking_number, request.user)
        if not appointment:
            raise Http404("Healthcare appointment not found or unauthorized access.")
        
        self.check_object_permissions(request, appointment)
        return Response({
            "success": True,
            "data": HealthcareAppointmentDetailSerializer(appointment).data,
        }, status=status.HTTP_200_OK)


class MedicalVisitNoteListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPatientOrAssignedHealthcareProvider]

    @extend_schema(
        operation_id="list_medical_visit_notes",
        summary="List Clinical Visit Notes",
        description="Returns immutable clinical visit observations and vitals recorded during home care.",
        responses={200: MedicalVisitNoteSerializer(many=True)},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request, booking_number):
        appointment = HealthcareSelector.get_appointment_by_booking_number(booking_number, request.user)
        if not appointment:
            raise Http404("Healthcare appointment not found.")
        self.check_object_permissions(request, appointment)
        notes = HealthcareSelector.get_clinical_notes_for_appointment(appointment)
        return Response({"success": True, "data": MedicalVisitNoteSerializer(notes, many=True).data})

    @extend_schema(
        operation_id="create_medical_visit_note",
        summary="Submit Clinical Visit Note",
        description="Assigned healthcare worker records patient vitals, clinical observations, and care recommendations.",
        request=MedicalVisitNoteCreateSerializer,
        responses={201: MedicalVisitNoteSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["Healthcare Ecosystem"],
    )
    def post(self, request, booking_number):
        appointment = HealthcareSelector.get_appointment_by_booking_number(booking_number, request.user)
        if not appointment:
            raise Http404("Healthcare appointment not found.")
        self.check_object_permissions(request, appointment)

        serializer = MedicalVisitNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            note = MedicalVisitNoteService.record_visit_note(
                appointment=appointment,
                author=request.user,
                validated_data=serializer.validated_data,
            )
            return Response({
                "success": True,
                "message": "Clinical visit note saved successfully.",
                "data": MedicalVisitNoteSerializer(note).data,
            }, status=status.HTTP_201_CREATED)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PatientInstructionAcknowledgeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="acknowledge_patient_instruction",
        summary="Acknowledge Pre-Visit Instruction",
        description="Patient confirms they have read and followed clinical prep instructions (e.g. fasting).",
        request=None,
        responses={200: PatientInstructionSerializer},
        tags=["Healthcare Ecosystem"],
    )
    def post(self, request, booking_number, instruction_id):
        appointment = HealthcareSelector.get_appointment_by_booking_number(booking_number, request.user)
        if not appointment:
            raise Http404("Healthcare appointment not found.")
        try:
            instruction = HealthcareAppointmentService.acknowledge_instruction(
                patient=request.user,
                appointment=appointment,
                instruction_id=instruction_id,
            )
            return Response({
                "success": True,
                "message": "Instruction acknowledged.",
                "data": PatientInstructionSerializer(instruction).data,
            }, status=status.HTTP_200_OK)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HealthcareProfessionalProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_healthcare_professional_profile",
        summary="Get Medical Credential Profile",
        description="Retrieves healthcare professional registration and licensing credentials.",
        responses={200: HealthcareProfessionalProfileSerializer},
        tags=["Healthcare Ecosystem"],
    )
    def get(self, request):
        profile = HealthcareSelector.get_healthcare_professional_profile(request.user)
        if not profile:
            profile = HealthcareProfessionalProfile.objects.create(
                professional=request.user,
                registration_number=f"PROV-{request.user.id}",
                registration_council="Pending Verification",
                medical_degree="Certified Practitioner",
            )
        return Response({"success": True, "data": HealthcareProfessionalProfileSerializer(profile).data})

    @extend_schema(
        operation_id="update_healthcare_professional_profile",
        summary="Update Medical Credential Profile",
        description="Updates registration number, council name, and degree qualifications.",
        request=HealthcareProfessionalProfileSerializer,
        responses={200: HealthcareProfessionalProfileSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["Healthcare Ecosystem"],
    )
    def put(self, request):
        serializer = HealthcareProfessionalProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile = HealthcareProfessionalService.update_credentials(request.user, serializer.validated_data)
            return Response({
                "success": True,
                "message": "Healthcare professional credentials updated.",
                "data": HealthcareProfessionalProfileSerializer(profile).data,
            }, status=status.HTTP_200_OK)
        except (ValueError, ValidationError) as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
