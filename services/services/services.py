from django.db import transaction
from django.utils.text import slugify
from services.models import ServiceGroup, Category, Service, ServicePackage, ServicePackageInclude
from services.choices import RequirementFieldType
from .selectors import ServiceRequirementSelector


class ServiceGroupService:

    @staticmethod
    @transaction.atomic
    def create(**data):
        """
        Create a new Service Group
        """
        return ServiceGroup.objects.create(**data)

    @staticmethod
    @transaction.atomic
    def update(service_group, **data):
        """
        Update an existing Service Group
        """
        for key, value in data.items():
            setattr(service_group, key, value)

        service_group.save()

        return service_group

    @staticmethod
    @transaction.atomic
    def delete(service_group):
        """
        Soft Delete
        """
        service_group.soft_delete()

    @staticmethod
    @transaction.atomic
    def restore(service_group):
        """
        Restore deleted Service Group
        """
        service_group.restore()

    @staticmethod
    @transaction.atomic
    def activate(service_group):
        service_group.is_active = True
        service_group.save(update_fields=["is_active"])

    @staticmethod
    @transaction.atomic
    def deactivate(service_group):
        service_group.is_active = False
        service_group.save(update_fields=["is_active"])

    @staticmethod
    @transaction.atomic
    def mark_featured(service_group):
        service_group.is_featured = True
        service_group.save(update_fields=["is_featured"])

    @staticmethod
    @transaction.atomic
    def remove_featured(service_group):
        service_group.is_featured = False
        service_group.save(update_fields=["is_featured"])


class CategoryService:

    @staticmethod
    def create(validated_data):

        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])

        return Category.objects.create(**validated_data)

    @staticmethod
    def update(category, validated_data):

        for field, value in validated_data.items():
            setattr(category, field, value)

        if not category.slug:
            category.slug = slugify(category.name)

        category.save()

        return category

    @staticmethod
    def delete(category):
        category.soft_delete()

    @staticmethod
    def restore(category):
        category.restore()


class ServiceService:

    @staticmethod
    def create(validated_data):

        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(
                validated_data["name"]
            )

        return Service.objects.create(**validated_data)

    @staticmethod
    def update(service, validated_data):

        for field, value in validated_data.items():
            setattr(service, field, value)

        if not service.slug:
            service.slug = slugify(service.name)

        service.save()

        return service

    @staticmethod
    def delete(service):

        service.soft_delete()

    @staticmethod
    def restore(service):

        service.restore()


class PackageService:

    @staticmethod
    def create(**data):
        return ServicePackage.objects.create(**data)

    @staticmethod
    def update(package,**data):
        for key,value in data.items(): setattr(package,key,value)
        package.save()
        return package

    @staticmethod
    def activate(package):
        package.is_active=True
        package.save(update_fields=["is_active"])

    @staticmethod
    def deactivate(package):
        package.is_active=False
        package.save(update_fields=["is_active"])


class PackageIncludeService:

    @staticmethod
    def create(**data):
        return ServicePackageInclude.objects.create(**data)

    @staticmethod
    def update(include,**data):
        for key,value in data.items(): setattr(include,key,value)
        include.save()
        return include

    @staticmethod
    def delete(include):
        include.delete()


class ServiceRequirementService:

    @staticmethod
    def validate(service, data):
        """
        Validate dynamic service requirements.

        Args:
            service: Service instance
            data: dict of submitted requirement values

        Returns:
            (is_valid, errors)
        """

        errors = {}

        requirements = ServiceRequirementSelector.service(service)

        for requirement in requirements:

            value = data.get(requirement.field_name)

            # Required validation
            if requirement.required and value in (None, "", []):
                errors[requirement.field_name] = (
                    f"{requirement.label} is required."
                )
                continue

            # Skip remaining checks if optional and empty
            if value in (None, "", []):
                continue

            # Choice validation
            if requirement.field_type in (
                RequirementFieldType.SELECT,
                RequirementFieldType.RADIO,
            ):
                if value not in requirement.choices:
                    errors[requirement.field_name] = (
                        f"Invalid value for {requirement.label}."
                    )

            # Checkbox validation
            if requirement.field_type == RequirementFieldType.CHECKBOX:

                if not isinstance(value, list):
                    errors[requirement.field_name] = (
                        f"{requirement.label} must be a list."
                    )

        return (
            len(errors) == 0,
            errors,
        )

    @staticmethod
    def extract_and_validate(service, post_data):

        requirements = ServiceRequirementSelector.service(service)

        data = {}

        for requirement in requirements:
            if requirement.field_type == RequirementFieldType.CHECKBOX:
                data[requirement.field_name] = post_data.getlist(
                    requirement.field_name
                )
            else:
                data[requirement.field_name] = post_data.get(
                    requirement.field_name
                )

        is_valid, errors = ServiceRequirementService.validate(
            service,
            data,
        )

        if not is_valid:
            raise ValueError(errors)

        return data