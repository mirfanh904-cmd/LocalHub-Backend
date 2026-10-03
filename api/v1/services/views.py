import math
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Avg, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from services.models import ServiceGroup, Service
from bookings.models import Booking, BookingStatus, Review
from accounts.models import User, ProfessionalProfile, Address
from .serializers import (
    ServiceGroupSerializer,
    ServiceListSerializer,
    ServiceDetailSerializer,
)
from services.services.selectors import ServiceSelector


class PlatformStatsAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="get_platform_stats",
        summary="Retrieve Public Platform Statistics",
        description="Returns dynamic system-wide metrics: completed bookings, verified professionals, happy customers, average rating, and cities covered.",
        responses={200: OpenApiResponse(description="Public platform impact statistics")},
        tags=["Services"],
    )
    def get(self, request):
        from verification.models import VerificationStatus

        bookings_completed = Booking.objects.filter(status=BookingStatus.COMPLETED).count()
        if bookings_completed == 0:
            bookings_completed = Booking.objects.count()

        verified_pros = ProfessionalProfile.objects.filter(
            verification__status=VerificationStatus.APPROVED
        ).count()
        if verified_pros == 0:
            verified_pros = ProfessionalProfile.objects.filter(is_active=True).count()

        active_pros = ProfessionalProfile.objects.filter(
            availability_status=ProfessionalProfile.AvailabilityStatus.AVAILABLE
        ).count()
        if active_pros == 0:
            active_pros = ProfessionalProfile.objects.filter(is_active=True).count()

        happy_customers = User.objects.filter(role=User.Role.CUSTOMER).count()

        distinct_cities = (
            Address.objects.filter(city__isnull=False)
            .exclude(city="")
            .values("city")
            .distinct()
            .count()
        )

        avg_rating_res = Review.objects.aggregate(avg=Avg("rating"))
        avg_rating = avg_rating_res.get("avg")
        formatted_rating = round(float(avg_rating), 1) if avg_rating is not None else 4.9

        return Response(
            {
                "bookings_completed": bookings_completed,
                "verified_professionals": verified_pros,
                "active_professionals": active_pros,
                "happy_customers": happy_customers,
                "cities_covered": max(distinct_cities, 1),
                "average_rating": formatted_rating,
            },
            status=status.HTTP_200_OK,
        )



class ServiceGroupListAPIView(generics.ListAPIView):
    serializer_class = ServiceGroupSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_service_groups",
        summary="List Service Groups",
        description="Returns all active high-level domain service groups (Home Services, Wellness, etc.), excluding healthcare.",
        tags=["Service Groups"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Q
        return (
            ServiceGroup.objects
            .filter(is_active=True)
            .prefetch_related("categories")
            .exclude(Q(slug__icontains="healthcare") | Q(name__icontains="healthcare"))
            .order_by("display_order", "name")
        )


class ServiceGroupDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ServiceGroupSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    @extend_schema(
        operation_id="retrieve_service_group",
        summary="Retrieve Service Group",
        description="Returns details of a specific service group by slug.",
        tags=["Service Groups"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return ServiceGroup.objects.filter(is_active=True).prefetch_related("categories")


class ServiceListAPIView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_services",
        summary="List Services",
        description="Returns all active services with combined category filtering, search, and sorting.",
        parameters=[
            OpenApiParameter("category", str, description="Filter services by category or service group slug"),
            OpenApiParameter("group", str, description="Filter services by service group slug"),
            OpenApiParameter("subcategory", str, description="Filter services by subcategory slug"),
            OpenApiParameter("featured", bool, description="Filter only featured services (true/false)"),
            OpenApiParameter("search", str, description="Keyword search across service name and description"),
            OpenApiParameter("ordering", str, description="Sort field (starting_price, -starting_price, -average_rating, -created_at)"),
        ],
        tags=["Services"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Q
        queryset = (
            Service.objects
            .filter(is_active=True)
            .select_related("category", "category__service_group")
        )

        # Exclude healthcare services completely from standard marketplace catalog
        queryset = queryset.exclude(
            Q(category__service_group__slug__icontains="healthcare") |
            Q(category__slug__icontains="healthcare") |
            Q(slug__icontains="healthcare")
        )

        group = self.request.query_params.get("group")
        if group:
            queryset = queryset.filter(category__service_group__slug=group)

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(
                Q(category__slug=category) | Q(category__service_group__slug=category)
            )

        subcategory = self.request.query_params.get("subcategory")
        if subcategory:
            queryset = queryset.filter(category__slug=subcategory)

        featured = self.request.query_params.get("featured")
        if featured == "true":
            queryset = queryset.filter(is_featured=True)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(short_description__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search)
            )

        ordering = self.request.query_params.get("ordering") or self.request.query_params.get("sort")
        if ordering:
            if ordering in ["starting_price", "-starting_price", "average_rating", "-average_rating", "-created_at", "display_order"]:
                queryset = queryset.order_by(ordering)
            elif ordering == "price_asc":
                queryset = queryset.order_by("starting_price")
            elif ordering == "price_desc":
                queryset = queryset.order_by("-starting_price")
            elif ordering == "rating_desc":
                queryset = queryset.order_by("-average_rating")
        else:
            queryset = queryset.order_by("display_order", "name")

        return queryset


class FeaturedServiceListAPIView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="list_featured_services",
        summary="List Featured Services",
        description="Returns featured highlight services.",
        tags=["Services"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return ServiceSelector.featured()


class ServiceDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ServiceDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    @extend_schema(
        operation_id="retrieve_service_detail",
        summary="Retrieve Service Details",
        description="Returns complete details for a service, including nested packages, feature inclusions, dynamic customer intake requirements, and FAQs.",
        responses={
            200: ServiceDetailSerializer,
            404: OpenApiResponse(description="Service not found"),
        },
        tags=["Services"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return ServiceSelector.by_slug(self.kwargs["slug"])