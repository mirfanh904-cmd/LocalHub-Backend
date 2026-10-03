from django.db import transaction
from accounts.models import FavouriteService as FavouriteServiceModel, FavouriteProfessional as FavouriteProfessionalModel


class FavouriteService:

    @staticmethod
    @transaction.atomic
    def toggle_service_favourite(user, service):
        fav, created = FavouriteServiceModel.objects.get_or_create(user=user, service=service)
        if not created:
            fav.delete()
            return False  # Removed from favorites
        return True  # Added to favorites

    @staticmethod
    @transaction.atomic
    def toggle_professional_favourite(user, professional):
        fav, created = FavouriteProfessionalModel.objects.get_or_create(user=user, professional=professional)
        if not created:
            fav.delete()
            return False  # Removed from favorites
        return True  # Added to favorites
