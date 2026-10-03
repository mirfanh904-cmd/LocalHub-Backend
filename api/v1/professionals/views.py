from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from accounts.models import ProfessionalProfile
from verification.trust_score_service import TrustScoreService
from .serializers import (
    ProfessionalListSerializer,
    ProfessionalDetailSerializer,
    TrustScoreResponseSerializer,
)


class ProfessionalListAPIView(generics.ListAPIView):
    serializer_class = ProfessionalListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_professionals",
        summary="List Professionals",
        description="Returns a paginated list of active verified and listed professionals with optional keyword search.",
        parameters=[
            OpenApiParameter("search", str, description="Search by professional name or title"),
            OpenApiParameter("service_slug", str, description="Filter professionals offering a specific service"),
        ],
        tags=["Professionals"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = ProfessionalProfile.objects.filter(user__is_active=True).select_related("user")
        search = self.request.query_params.get("search")
        service_slug = self.request.query_params.get("service_slug")

        if service_slug:
            qs = qs.filter(services__service__slug=service_slug, services__is_active=True)
        if search:
            qs = qs.filter(
                user__first_name__icontains=search
            ) | qs.filter(
                user__last_name__icontains=search
            ) | qs.filter(
                professional_title__icontains=search
            )
        return qs.distinct().order_by("-average_rating", "-reviews_count")


class FeaturedProfessionalsAPIView(generics.ListAPIView):
    serializer_class = ProfessionalListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_featured_professionals",
        summary="List Featured Professionals",
        description="Returns top-tier, highly-rated verified professionals.",
        tags=["Professionals"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return (
            ProfessionalProfile.objects
            .filter(user__is_active=True, average_rating__gte=4.0)
            .select_related("user")
            .order_by("-average_rating", "-reviews_count")[:8]
        )


class ProfessionalDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ProfessionalDetailSerializer
    permission_classes = [AllowAny]
    queryset = (
        ProfessionalProfile.objects
        .filter(user__is_active=True)
        .select_related("user")
        .prefetch_related("services", "services__service", "skills", "languages")
    )

    @extend_schema(
        operation_id="retrieve_professional_detail",
        summary="Retrieve Professional Profile",
        description="Returns detailed profile information, skills, offered services, and rating metrics for a professional.",
        tags=["Professionals"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ProfessionalTrustScoreAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="get_professional_trust_score",
        summary="Retrieve Professional Trust Score",
        description="Calculates and returns the deterministic Trust Score, trust badge tier (Elite/Trusted/Good), and detailed signal breakdown for a professional.",
        responses={
            200: TrustScoreResponseSerializer,
            404: OpenApiResponse(description="Professional profile not found"),
        },
        tags=["Trust & Safety"],
    )
    def get(self, request, pk):
        profile = get_object_or_404(ProfessionalProfile, id=pk)
        breakdown = TrustScoreService.calculate_score_for_profile(profile)
        return Response(
            {"success": True, "data": breakdown},
            status=status.HTTP_200_OK,
        )
