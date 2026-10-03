from accounts.forms import AddressForm
from accounts.models import Address
from django.shortcuts import get_object_or_404
from django.db import transaction  #  delete chythal default address avan use cheyyunnu

class AddressService:

    @staticmethod
    def list(user):

        return Address.objects.filter(
            user=user,
            is_active=True,
        ).order_by(
            "-is_default",
            "-created_at",
        )

    @staticmethod
    def get():

        return AddressForm()

    @staticmethod
    def create(user, data):
        form = AddressForm(
            data,
            user=user,
        )
        if form.is_valid():

            address = form.save(commit=False)

            address.user = user

            # First active address → automatically default
            if not Address.objects.filter(
                    user=user,
                    is_active=True,
            ).exists():

                address.is_default = True

            # If user selected "Make Default",
            # remove old default first
            elif address.is_default:

                Address.objects.filter(
                    user=user,
                    is_active=True,
                ).update(
                    is_default=False,
                )

            address.save()

            return True, form

        return False, form


    @staticmethod
    def get_address_form(user, pk):

        address = get_object_or_404(
            Address,
            pk=pk,
            user=user,
        )

        return address, AddressForm(instance=address)

    @staticmethod
    def get_form(instance=None):
        return AddressForm(instance=instance)
    @staticmethod
    def update(user, pk, data):

        address = get_object_or_404(
            Address,
            pk=pk,
            user=user,
        )

        form = AddressForm(
            data,
            instance=address,
            user=user,
        )

        if form.is_valid():
            form.save()

            return True, form

        return False, form

    @staticmethod
    @transaction.atomic()
    def make_default(user, pk):
        Address.objects.filter(
            user=user,
            is_active=True
        ).update(
            is_default=False,
        )
        address = get_object_or_404(
            Address,
            pk=pk,
            user=user,
        )
        address.is_default = True
        address.save()

    @staticmethod
    @transaction.atomic
    def delete(user, pk):

        address = get_object_or_404(
            Address,
            pk=pk,
            user=user,
            is_active=True,
        )

        was_default = address.is_default

        address.soft_delete()

        address.is_default = False
        address.save(update_fields=["is_default"])

        if was_default:

            next_address = (
                Address.objects.filter(
                    user=user,
                    is_active=True,
                )
                .exclude(pk=address.pk)
                .order_by("-created_at")
                .first()
            )

            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=["is_default"])

    @staticmethod
    def apply_create_rules(user, serializer):

        serializer.validated_data["user"] = user

        active_addresses = Address.objects.filter(
            user=user,
            is_active=True,
        )

        # First address
        if not active_addresses.exists():

            serializer.validated_data["is_default"] = True

        # New address selected as default
        elif serializer.validated_data.get("is_default"):

            active_addresses.update(
                is_default=False,
            )