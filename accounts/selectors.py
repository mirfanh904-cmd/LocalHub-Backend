from .models import Address, FavouriteService, FavouriteProfessional


class FavouriteSelector:

    @staticmethod
    def user_favourite_services(user):
        return FavouriteService.objects.filter(user=user).select_related("service", "service__category")

    @staticmethod
    def user_favourite_professionals(user):
        return FavouriteProfessional.objects.filter(user=user).select_related("professional", "professional__user")

    @staticmethod
    def is_service_favourited(user, service):
        if not user.is_authenticated:
            return False
        return FavouriteService.objects.filter(user=user, service=service).exists()

    @staticmethod
    def is_professional_favourited(user, professional):
        if not user.is_authenticated:
            return False
        return FavouriteProfessional.objects.filter(user=user, professional=professional).exists()


class AddressSelector:

    @staticmethod
    def user_addresses(user):

        return (
            Address.objects
            .filter(
                user=user,
                deleted_at__isnull=True,)
            .order_by(
                "-is_default",
                "-created_at",
            )
        )