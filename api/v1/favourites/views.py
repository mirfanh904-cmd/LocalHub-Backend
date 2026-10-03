from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse

from services.models import Service
from accounts.models import ProfessionalProfile
from accounts.services import FavouriteService
from accounts.selectors import FavouriteSelector
from .serializers import FavouriteServiceSerializer, FavouriteProfessionalSerializer


class ToggleFavouriteServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="toggle_favourite_service",
        summary="Toggle Favourite Service",
        description="Adds or removes a service from the customer's favourites bookmark list.",
        request=None,
        responses={200: OpenApiResponse(description="Toggle status returned")},
        tags=["Favourites"],
    )
    def post(self, request, service_id):
        service = get_object_or_404(Service, id=service_id)
        is_fav = FavouriteService.toggle_service_favourite(request.user, service)
        return Response(
            {"success": True, "is_favourited": is_fav},
            status=status.HTTP_200_OK
        )


class ToggleFavouriteProfessionalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="toggle_favourite_professional",
        summary="Toggle Favourite Professional",
        description="Adds or removes a professional worker from the customer's favourites bookmark list.",
        request=None,
        responses={200: OpenApiResponse(description="Toggle status returned")},
        tags=["Favourites"],
    )
    def post(self, request, professional_id):
        professional = get_object_or_404(ProfessionalProfile, id=professional_id)
        is_fav = FavouriteService.toggle_professional_favourite(request.user, professional)
        return Response(
            {"success": True, "is_favourited": is_fav},
            status=status.HTTP_200_OK
        )


class FavouriteServiceListAPIView(generics.ListAPIView):
    serializer_class = FavouriteServiceSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_favourite_services",
        summary="List Favourite Services",
        description="Returns list of services bookmarked by the authenticated user.",
        tags=["Favourites"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return FavouriteSelector.user_favourite_services(self.request.user)


class FavouriteProfessionalListAPIView(generics.ListAPIView):
    serializer_class = FavouriteProfessionalSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_favourite_professionals",
        summary="List Favourite Professionals",
        description="Returns list of professionals bookmarked by the authenticated user.",
        tags=["Favourites"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return FavouriteSelector.user_favourite_professionals(self.request.user)
