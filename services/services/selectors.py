from services.models import ServiceGroup, Category,\
    Service, ServicePackage, ServiceRequirement, ServiceFAQ


class ServiceGroupSelector:

    @staticmethod
    def all():
        """
        Return all active service groups ordered by display order.
        """
        return (
            ServiceGroup.objects
            .filter(is_active=True)
            .order_by("display_order", "name")
        )

    @staticmethod
    def featured():
        """
        Return featured service groups.
        """
        return (
            ServiceGroup.objects
            .filter(
                is_active=True,
                is_featured=True
            )
            .order_by("display_order", "name")
        )

    @staticmethod
    def by_slug(slug):
        """
        Return a single active service group.
        """
        return (
            ServiceGroup.objects
            .filter(
                is_active=True,
                slug=slug
            )
            .first()
        )


class CategorySelector:

    @staticmethod
    def all():
        return Category.objects.filter(
            is_active=True
        ).select_related(
            "service_group"
        ).order_by(
            "display_order",
            "name"
        )

    @staticmethod
    def featured():
        return Category.objects.filter(
            is_active=True,
            is_featured=True
        ).select_related(
            "service_group"
        ).order_by(
            "display_order",
            "name"
        )

    @staticmethod
    def by_slug(slug):
        return Category.objects.select_related(
            "service_group"
        ).get(
            slug=slug,
            is_active=True
        )

    @staticmethod
    def by_service_group(group_slug):
        return Category.objects.filter(
            service_group__slug=group_slug,
            is_active=True
        ).select_related(
            "service_group"
        ).order_by(
            "display_order",
            "name"
        )

    @staticmethod
    def search(query):
        return (
            Category.objects
            .filter(
                name__icontains=query,
                is_active=True,
            )
            .select_related("service_group")
            .order_by("display_order", "name")
        )


class ServiceSelector:

    @staticmethod
    def all():

        return (
            Service.objects
            .filter(is_active=True)
            .select_related(
                "category",
                "category__service_group"
            )
            .order_by(
                "display_order",
                "name"
            )
        )

    @staticmethod
    def featured():

        return (
            Service.objects
            .filter(
                is_active=True,
                is_featured=True,
            )
            .select_related(
                "category",
                "category__service_group"
            )
        )

    @staticmethod
    def by_slug(slug):

        return (
            Service.objects
            .select_related(
                "category",
                "category__service_group"
            )
            .get(
                slug=slug,
                is_active=True,
            )
        )

    @staticmethod
    def by_category(category_slug):

        return (
            Service.objects
            .filter(
                category__slug=category_slug,
                is_active=True,
            )
            .select_related(
                "category",
                "category__service_group"
            )
            .order_by(
                "display_order",
                "name"
            )
        )

    @staticmethod
    def search(query):

        return (
            Service.objects
            .filter(
                name__icontains=query,
                is_active=True,
            )
            .select_related(
                "category",
                "category__service_group"
            )
        )

    @staticmethod
    def by_service_group(group_slug):

        return (
            Service.objects
            .filter(
                category__service_group__slug=group_slug,
                is_active=True,
            )
            .select_related(
                "category",
                "category__service_group",
            )
            .order_by(
                "display_order",
                "name",
            )
        )

    @staticmethod
    def filter(group=None, category=None):

        queryset = (
            Service.objects
            .filter(is_active=True)
            .select_related(
                "category",
                "category__service_group",
            )
        )

        if group:
            queryset = queryset.filter(
                category__service_group__slug=group
            )

        if category:
            queryset = queryset.filter(
                category__slug=category
            )

        return queryset.order_by(
            "display_order",
            "name",
        )

    @staticmethod
    def get_by_slug(slug):
        return (
            Service.objects
            .select_related(
                "category",
                "category__service_group",
            )
            .filter(
                slug=slug,
                is_active=True,
            )
            .first()
        )

    @staticmethod
    def related(service):

        return (
            Service.objects
            .select_related(
                "category",
                "category__service_group",
            )
            .filter(
                category=service.category,
                is_active=True,
            )
            .exclude(
                id=service.id,
            )[:4]
        )


class PackageSelector:

    @staticmethod
    def all():
        return ServicePackage.objects.filter(is_active=True).select_related("service").prefetch_related("features")

    @staticmethod
    def service(service):
        return ServicePackage.objects.filter(service=service, is_active=True).prefetch_related("features")

    @staticmethod
    def detail(slug):
        return ServicePackage.objects.select_related("service").prefetch_related("features").filter(slug=slug,
                                                                                                    is_active=True).first()


class ServiceRequirementSelector:

    @staticmethod
    def all():
        return (
            ServiceRequirement.objects
            .filter(is_active=True)
            .select_related("service")
            .order_by("service", "sort_order")
        )

    @staticmethod
    def service(service):
        return (
            ServiceRequirement.objects
            .filter(
                service=service,
                is_active=True
            )
            .order_by("sort_order", "id")
        )

    @staticmethod
    def by_field_name(service, field_name):
        return (
            ServiceRequirement.objects
            .filter(
                service=service,
                field_name=field_name,
                is_active=True
            )
            .first()
        )

    @staticmethod
    def count(service):
        return (
            ServiceRequirement.objects
            .filter(
                service=service,
                is_active=True
            )
            .count()
        )


class ServiceFAQSelector:

    @staticmethod
    def service(service):
        return (
            ServiceFAQ.objects
            .filter(
                service=service,
                is_active=True
            )
            .order_by("sort_order", "id")
        )