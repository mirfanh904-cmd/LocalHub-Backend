from django.db import models
from django.utils.text import slugify
from .choices import RequirementFieldType
from common.models import BaseModel  # <-- BaseModel evide aano avide ninn import cheyyu


class ServiceGroup(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    short_description = models.CharField(
        max_length=255,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    icon_class = models.CharField(
        max_length=100,
        blank=True,
        default="bi-grid"
    )

    cover_image = models.ImageField(
        upload_to="service-groups/covers/",
        blank=True,
        null=True
    )

    theme_color = models.CharField(
        max_length=7,
        default="#2563EB",
        help_text="Hex color (Example: #2563EB)"
    )

    display_order = models.PositiveIntegerField(
        default=0
    )

    is_featured = models.BooleanField(
        default=False
    )

    seo_title = models.CharField(
        max_length=150,
        blank=True
    )

    seo_description = models.TextField(
        blank=True
    )

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Service Group"
        verbose_name_plural = "Service Groups"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)


class Category(BaseModel):
    service_group = models.ForeignKey(ServiceGroup, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    short_description = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="categories/covers/", blank=True, null=True)
    bootstrap_icon = models.CharField(max_length=100, default="bi-grid")
    theme_color = models.CharField(max_length=20, default="#2563EB")
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)

    class Meta:
        ordering = ["display_order", "name"]
        unique_together = ["service_group", "name"]

    def __str__(self):
        return f"{self.service_group.name} - {self.name}"


class Service(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    short_description = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    cover_image = models.ImageField(upload_to="services/", blank=True, null=True)

    icon_class = models.CharField(max_length=100, blank=True)

    starting_price = models.DecimalField(max_digits=10, decimal_places=2)

    estimated_duration = models.CharField(max_length=50, blank=True)

    theme_color = models.CharField(max_length=20, default="#2563EB")

    display_order = models.PositiveIntegerField(default=0)

    seo_title = models.CharField(max_length=150, blank=True)
    seo_description = models.TextField(blank=True)

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    reviews_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class ServicePackage(BaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=200)
    short_description = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.DurationField()
    sort_order = models.PositiveIntegerField(default=0)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "services_packages"
        ordering = ["sort_order", "price"]
        constraints = [models.UniqueConstraint(fields=["service", "slug"], name="unique_service_package")]

    def __str__(self):
        return f"{self.service.name} - {self.name}"

    def save(self, *args, **kwargs):
        if self.is_popular:
            ServicePackage.objects.filter(service=self.service, is_popular=True).exclude(pk=self.pk).update(
                is_popular=False)
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class ServicePackageInclude(BaseModel):
    package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name="features")
    title = models.CharField(max_length=200)
    icon = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "services_package_features"
        ordering = ["sort_order"]

    def __str__(self):
        return self.title


class ServiceRequirement(BaseModel):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="requirements"
    )



    label = models.CharField(
        max_length=150
    )

    field_name = models.SlugField(
        max_length=100,
        help_text="Unique identifier (example: bedrooms)"
    )

    field_type = models.CharField(
        max_length=20,
        choices=RequirementFieldType.choices,
        default=RequirementFieldType.TEXT
    )

    placeholder = models.CharField(
        max_length=255,
        blank=True
    )

    help_text = models.CharField(
        max_length=255,
        blank=True
    )

    choices = models.JSONField(
        default=list,
        blank=True,
        help_text='Example: ["1","2","3"]'
    )

    default_value = models.CharField(
        max_length=255,
        blank=True
    )

    required = models.BooleanField(
        default=True
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["sort_order", "id"]
        unique_together = ("service", "field_name")
        verbose_name = "Service Requirement"
        verbose_name_plural = "Service Requirements"

    def __str__(self):
        return f"{self.service.name} - {self.label}"


class ServiceFAQ(BaseModel):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="faqs"
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Service FAQ"
        verbose_name_plural = "Service FAQs"

    def __str__(self):
        return f"{self.service.name} - {self.question}"