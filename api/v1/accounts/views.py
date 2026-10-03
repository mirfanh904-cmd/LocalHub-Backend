from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from accounts.models import Address, User, ProfessionalProfile, Skill
from accounts.services.address_service import AddressService
from healthcare.models import (
    HealthcareProfessionalProfile,
    HealthcareOrganization,
    OrganizationMembership,
    OrganizationVerificationDocument,
    OrganizationRole,
)
from verification.models import (
    ProfessionalVerification,
    ProfessionalVerificationDocument,
    VerificationStatus,
    DocumentStatus,
    DocumentType,
)
from .serializers import (
    AddressSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserCapabilitiesSerializer,
    BecomeIndividualProSerializer,
    BecomeHealthcareProSerializer,
    BecomeOrganizationSerializer,
)


class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_user_profile",
        summary="Retrieve User Profile",
        description="Returns detailed profile information for the authenticated user, including role and verification status.",
        responses={200: UserProfileSerializer},
        tags=["Accounts"],
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="update_user_profile",
        summary="Update User Profile",
        description="Updates profile details such as name, phone number, and avatar image for the authenticated user.",
        request=UserProfileUpdateSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["Accounts"],
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "success": True,
                "message": "Profile updated successfully.",
                "data": UserProfileSerializer(request.user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class UserCapabilitiesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_user_capabilities",
        summary="Get User Role Capabilities",
        description="Returns multi-role capabilities (customer, individual pro, healthcare pro, organization owner/member).",
        responses={200: UserCapabilitiesSerializer},
        tags=["Accounts"],
    )
    def get(self, request):
        user = request.user
        has_pro_profile = hasattr(user, "professional_profile")
        has_healthcare_profile = hasattr(user, "healthcare_profile")
        
        owned_orgs = HealthcareOrganization.objects.filter(owner=user)
        memberships = OrganizationMembership.objects.filter(user=user, is_active=True).select_related("organization")

        verification_status = None
        if has_pro_profile:
            ver = getattr(user.professional_profile, "verification", None)
            if ver:
                verification_status = ver.status

        org_list = []
        for org in owned_orgs:
            org_list.append({
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "type": org.organization_type,
                "role": "owner",
                "is_verified": org.is_verified,
            })
        for m in memberships:
            if not any(o["id"] == m.organization.id for o in org_list):
                org_list.append({
                    "id": m.organization.id,
                    "name": m.organization.name,
                    "slug": m.organization.slug,
                    "type": m.organization.organization_type,
                    "role": m.role,
                    "is_verified": m.organization.is_verified,
                })

        data = {
            "is_customer": True,
            "is_individual_pro": has_pro_profile and not has_healthcare_profile,
            "is_healthcare_pro": has_healthcare_profile,
            "is_organization_owner": owned_orgs.exists(),
            "is_organization_member": memberships.exists(),
            "pro_verification_status": verification_status,
            "organizations": org_list,
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class BecomeIndividualProAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="become_individual_pro",
        summary="Onboard as Individual Professional",
        description="Upgrades customer account into a verified individual service professional (Cleaner, Electrician, Plumber, etc.).",
        request=BecomeIndividualProSerializer,
        responses={201: OpenApiResponse(description="Professional profile and verification submitted")},
        tags=["Accounts"],
    )
    def post(self, request):
        serializer = BecomeIndividualProSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        val = serializer.validated_data

        user = request.user
        # Preserve customer capabilities and update role
        if user.role == User.Role.CUSTOMER:
            user.role = User.Role.PROFESSIONAL
            user.save(update_fields=["role"])

        pro_profile, _ = ProfessionalProfile.objects.get_or_create(
            user=user,
            defaults={
                "professional_title": val["professional_title"],
                "bio": val["bio"],
                "experience_years": val["experience_years"],
                "hourly_rate": val.get("hourly_rate", 299),
                "working_radius": val.get("working_radius", 15),
            },
        )
        pro_profile.professional_title = val["professional_title"]
        pro_profile.bio = val["bio"]
        pro_profile.experience_years = val["experience_years"]
        pro_profile.hourly_rate = val.get("hourly_rate", pro_profile.hourly_rate)
        pro_profile.working_radius = val.get("working_radius", pro_profile.working_radius)
        pro_profile.save()

        # Handle skills
        if val.get("skills"):
            for skill_name in val["skills"]:
                skill_obj, _ = Skill.objects.get_or_create(
                    name=skill_name,
                    defaults={"slug": skill_name.lower().replace(" ", "-")}
                )
                pro_profile.skills.add(skill_obj)

        # Verification record
        ver, _ = ProfessionalVerification.objects.get_or_create(
            professional=pro_profile,
            defaults={"status": VerificationStatus.UNDER_REVIEW, "submitted_at": timezone.now()},
        )
        ver.status = VerificationStatus.UNDER_REVIEW
        ver.submitted_at = timezone.now()
        ver.save()

        # Document upload
        if val.get("document_file"):
            doc_type = val.get("document_type", DocumentType.AADHAAR)
            doc_num = val.get("document_number", f"ID-{user.id}")
            ProfessionalVerificationDocument.objects.create(
                verification=ver,
                document_type=doc_type,
                document_number=doc_num,
                document_file=val["document_file"],
                status=DocumentStatus.PENDING,
            )

        return Response({
            "success": True,
            "message": "Individual professional application submitted for review.",
            "data": {
                "professional_id": pro_profile.id,
                "verification_status": ver.status,
            }
        }, status=status.HTTP_201_CREATED)


class BecomeHealthcareProAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="become_healthcare_pro",
        summary="Onboard as Healthcare Professional",
        description="Registers credentials for doctors, nurses, physiotherapists, and clinical specialists.",
        request=BecomeHealthcareProSerializer,
        responses={201: OpenApiResponse(description="Healthcare professional application submitted")},
        tags=["Accounts"],
    )
    def post(self, request):
        serializer = BecomeHealthcareProSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        val = serializer.validated_data

        user = request.user
        if user.role == User.Role.CUSTOMER:
            user.role = User.Role.PROFESSIONAL
            user.save(update_fields=["role"])

        # Base Pro Profile
        pro_profile, _ = ProfessionalProfile.objects.get_or_create(
            user=user,
            defaults={
                "professional_title": f"{val['medical_degree']} - {val['clinical_specialty']}",
                "bio": val["bio"],
                "experience_years": val["years_of_clinical_exp"],
                "hourly_rate": val.get("hourly_rate", 799),
            },
        )
        pro_profile.professional_title = f"{val['medical_degree']} - {val['clinical_specialty']}"
        pro_profile.bio = val["bio"]
        pro_profile.experience_years = val["years_of_clinical_exp"]
        pro_profile.hourly_rate = val.get("hourly_rate", pro_profile.hourly_rate)
        pro_profile.save()

        # Healthcare Profile
        h_profile, _ = HealthcareProfessionalProfile.objects.get_or_create(
            professional=user,
            defaults={
                "medical_degree": val["medical_degree"],
                "clinical_specialty": val["clinical_specialty"],
                "registration_number": val["registration_number"],
                "registration_council": val["registration_council"],
                "years_of_clinical_exp": val["years_of_clinical_exp"],
            },
        )
        h_profile.medical_degree = val["medical_degree"]
        h_profile.clinical_specialty = val["clinical_specialty"]
        h_profile.registration_number = val["registration_number"]
        h_profile.registration_council = val["registration_council"]
        h_profile.years_of_clinical_exp = val["years_of_clinical_exp"]
        h_profile.save()

        # Verification record
        ver, _ = ProfessionalVerification.objects.get_or_create(
            professional=pro_profile,
            defaults={"status": VerificationStatus.UNDER_REVIEW, "submitted_at": timezone.now()},
        )
        ver.status = VerificationStatus.UNDER_REVIEW
        ver.submitted_at = timezone.now()
        ver.save()

        # Document upload
        if val.get("document_file"):
            doc_type = val.get("document_type", DocumentType.MEDICAL_COUNCIL_REGISTRATION)
            doc_num = val.get("registration_number", f"REG-{user.id}")
            ProfessionalVerificationDocument.objects.create(
                verification=ver,
                document_type=doc_type,
                document_number=doc_num,
                document_file=val["document_file"],
                status=DocumentStatus.PENDING,
            )

        return Response({
            "success": True,
            "message": "Healthcare professional credentials submitted for verification.",
            "data": {
                "healthcare_profile_id": h_profile.id,
                "verification_status": ver.status,
            }
        }, status=status.HTTP_201_CREATED)


class BecomeOrganizationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="become_organization",
        summary="Register Healthcare Organization",
        description="Registers a clinic, hospital, diagnostic center, or agency under the authenticated user.",
        request=BecomeOrganizationSerializer,
        responses={201: OpenApiResponse(description="Organization registered and pending verification")},
        tags=["Accounts"],
    )
    def post(self, request):
        serializer = BecomeOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        val = serializer.validated_data

        user = request.user
        org = HealthcareOrganization.objects.create(
            owner=user,
            name=val["name"],
            organization_type=val["organization_type"],
            registration_number=val["registration_number"],
            license_number=val.get("license_number", ""),
            contact_email=val["contact_email"],
            contact_phone=val["contact_phone"],
            address=val["address"],
            city=val.get("city", ""),
            state=val.get("state", ""),
            postal_code=val.get("postal_code", ""),
            description=val.get("description", ""),
            verification_status=VerificationStatus.UNDER_REVIEW,
        )

        # Create Owner Membership
        pro_profile = getattr(user, "professional_profile", None)
        OrganizationMembership.objects.create(
            organization=org,
            user=user,
            professional_profile=pro_profile,
            role=OrganizationRole.OWNER,
            is_active=True,
        )

        # Upload org verification document
        if val.get("document_file"):
            OrganizationVerificationDocument.objects.create(
                organization=org,
                document_type=val.get("document_type", "trade_license"),
                document_number=val.get("registration_number", ""),
                document_file=val["document_file"],
                status=DocumentStatus.PENDING,
            )

        return Response({
            "success": True,
            "message": "Organization registration submitted for verification.",
            "data": {
                "organization_id": org.id,
                "organization_name": org.name,
                "slug": org.slug,
                "verification_status": org.verification_status,
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_user_addresses",
        summary="List Customer Addresses",
        description="Returns all active addresses saved in the authenticated customer's address book.",
        tags=["Addresses"],
    ),
    create=extend_schema(
        operation_id="create_user_address",
        summary="Create Customer Address",
        description="Adds a new address to the authenticated customer's address book.",
        tags=["Addresses"],
    ),
    retrieve=extend_schema(
        operation_id="retrieve_user_address",
        summary="Retrieve Address Details",
        description="Returns detailed information for a specific address.",
        tags=["Addresses"],
    ),
    update=extend_schema(
        operation_id="update_user_address",
        summary="Update Address",
        description="Updates all fields of an existing address.",
        tags=["Addresses"],
    ),
    partial_update=extend_schema(
        operation_id="partial_update_user_address",
        summary="Partial Update Address",
        description="Updates specific fields of an existing address.",
        tags=["Addresses"],
    ),
    destroy=extend_schema(
        operation_id="delete_user_address",
        summary="Delete Address",
        description="Soft-deletes an address from the authenticated customer's address book.",
        tags=["Addresses"],
    ),
)
class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(
            user=self.request.user,
            is_active=True,
        ).order_by("-is_default", "-created_at")

    def perform_destroy(self, instance):
        instance.soft_delete()

    def perform_create(self, serializer):
        AddressService.apply_create_rules(
            self.request.user,
            serializer,
        )
        serializer.save(
            user=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save()
