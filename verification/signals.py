from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import ProfessionalProfile
from .services import VerificationService


@receiver(post_save, sender=ProfessionalProfile)
def create_professional_verification(sender, instance, created, **kwargs):
    if created:
        VerificationService.create_verification(instance)