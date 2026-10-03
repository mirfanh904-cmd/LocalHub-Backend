
from accounts.models import (
    ProfessionalProfile,
    ProfessionalService,
)

class ProfessionalSelector:

    @staticmethod
    def all():

        return (
            ProfessionalProfile.objects
            .filter(
                user__is_active=True,
            )
            .select_related(
                "user",
            )
        )

    @staticmethod
    def by_service(service):

        return (
            ProfessionalService.objects
            .filter(
                service=service,
                is_active=True,
                professional__user__is_active=True,
            )
            .select_related(
                "professional",
                "professional__user",
                "service",
            )
        )

    @staticmethod
    def detail(user_id):

        return (
            ProfessionalProfile.objects
            .select_related(
                "user",
            )
            .prefetch_related(
                "services",
                "services__service",
                "skills",
                "languages",
            )
            .filter(
                    user_id=user_id,            )
            .first()
        )

    @staticmethod
    def featured(limit=8):

        return (
            ProfessionalProfile.objects
            .filter(
                user__is_active=True,
            )[:limit]
        )

    @staticmethod
    def top_rated(limit=10):

        return (
            ProfessionalProfile.objects
            .filter(
                user__is_active=True,
            )[:limit]
        )

    @staticmethod
    def get_profile(user_slug):
        return (
            ProfessionalProfile.objects
            .select_related(
                "user",
            )
            .prefetch_related(
                "services",
                "skills",
                "languages",
            )
            .filter(
                user__slug=user_slug,
            )
            .first()
        )

    @staticmethod
    def professional_service(
            professional_id,
            service,
    ):
        return (
            ProfessionalService.objects
            .select_related(
                "professional",
                "professional__user",
                "service",
            )
            .filter(
                professional__user_id=professional_id,
                service=service,
                is_active=True,
            )
            .first()
        )

