import uuid
from django.utils.text import slugify
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from services.models import Service
from phonenumber_field.modelfields import PhoneNumberField

from common.models import BaseModel
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        PROFESSIONAL = "PROFESSIONAL", "Professional"

    class LoginProvider(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        GOOGLE = "GOOGLE", "Google"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    email = models.EmailField(
        unique=True,
    )

    phone = PhoneNumberField(
        unique=True,
        null=True,
        blank=True,
    )

    first_name = models.CharField(
        max_length=100,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    login_provider = models.CharField(
        max_length=20,
        choices=LoginProvider.choices,
        default=LoginProvider.EMAIL,
    )

    is_email_verified = models.BooleanField(
        default=False,
    )

    is_phone_verified = models.BooleanField(
        default=False,
    )

    profile_completed = models.BooleanField(
        default=False,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_staff = models.BooleanField(
        default=False,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "first_name",
    ]

    class Meta:
        db_table = "accounts_users"
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    @property
    def full_name(self):
        return " ".join(filter(None, [self.first_name, self.last_name]))

    def __str__(self):
        return self.full_name or self.email

    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(self.full_name)

            slug = base_slug

            counter = 1

            while User.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"

                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

class UserProfile(BaseModel):
    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class Language(models.TextChoices):
        ENGLISH = "ENGLISH", "English"
        MALAYALAM = "MALAYALAM", "Malayalam"
        HINDI = "HINDI", "Hindi"
        TAMIL = "TAMIL", "Tamil"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True,
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
    )

    bio = models.TextField(
        blank=True,
    )
    preferred_language = models.CharField(
        max_length=20,
        choices=Language.choices,
        default=Language.ENGLISH,
    )
    occupation = models.CharField(
        max_length=100,
        blank=True,
    )
    city = models.CharField(
        max_length=100,
        blank=True,
    )

    state = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="India",
    )


    class Meta:
        db_table = "accounts_user_profiles"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.full_name}'s Profile"


class Address(BaseModel):
    class AddressType(models.TextChoices):
        HOME = "HOME", "🏠 Home"
        WORK = "WORK", "🏢 Work"
        OTHER = "OTHER", "📍 Other"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.HOME,
    )
    house_name = models.CharField(max_length=200)
    area = models.CharField(max_length=200)
    landmark = models.CharField(
        max_length=200,
        blank=True,
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(
        max_length=100,
        default="India",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    postal_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_addresses"

    def __str__(self):
        return f"{self.full_name} - {self.city}"

class Skill(BaseModel):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        unique=True,
    )

    class Meta:
        db_table = "accounts_skills"

    def __str__(self):
        return self.name

class Language(BaseModel):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=10,
        unique=True,
    )

    class Meta:
        db_table = "accounts_languages"

    def __str__(self):
        return self.name


class ProfessionalProfile(BaseModel):
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        BUSY = "BUSY", "Busy"
        OFFLINE = "OFFLINE", "Offline"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="professional_profile")
    professional_title = models.CharField(
        max_length=150,
    )
    bio = models.TextField()

    experience_years = models.PositiveIntegerField(
        default=0,
    )
    languages = models.ManyToManyField(
        Language,
        blank=True,
        related_name="professionals",
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    minimum_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    working_radius = models.PositiveIntegerField(
        default=10,
        help_text="Radius in KM",
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )

    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="professionals",
    )
    profile_photo = models.ImageField(
        upload_to="professionals/profile_photos/",
        blank=True,
        null=True,
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    reviews_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "accounts_professional_profiles"

    @property
    def is_verified(self):
        verification = getattr(self, "verification", None)
        return verification is not None and verification.status == "approved"

    def __str__(self):
        return self.user.first_name

class ProfessionalService(BaseModel):

    professional = models.ForeignKey(
        ProfessionalProfile,
        on_delete=models.CASCADE,
        related_name="services",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="professionals",
    )

    custom_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override default service price",
    )

    estimated_duration = models.DurationField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_featured = models.BooleanField(
        default=False,
    )
    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:

        db_table = "accounts_professional_services"

        ordering = [
            "display_order",
            "service__name",
        ]
        constraints = [

            models.UniqueConstraint(
                fields=[
                    "professional",
                    "service",
                ],
                name="unique_professional_service",
            )

        ]


    def __str__(self):

        return f"{self.professional.user.full_name} - {self.service.name}"


class FavouriteService(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favourite_services")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="favourited_by")

    class Meta:
        db_table = "accounts_favourite_services"
        unique_together = ("user", "service")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.service.name}"


class FavouriteProfessional(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favourite_professionals")
    professional = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="favourited_by")

    class Meta:
        db_table = "accounts_favourite_professionals"
        unique_together = ("user", "professional")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.professional.user.full_name}"