from rest_framework import serializers
from accounts.models import FavouriteService, FavouriteProfessional
from api.v1.services.serializers import ServiceSerializer


class FavouriteServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)

    class Meta:
        model = FavouriteService
        fields = ["id", "service", "created_at"]


class FavouriteProfessionalSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.user.full_name", read_only=True)
    professional_title = serializers.CharField(source="professional.professional_title", read_only=True)
    average_rating = serializers.DecimalField(source="professional.average_rating", max_digits=3, decimal_places=2, read_only=True)

    class Meta:
        model = FavouriteProfessional
        fields = [
            "id",
            "professional",
            "professional_name",
            "professional_title",
            "average_rating",
            "created_at",
        ]
