from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from accounts.services import ProfileService, AddressService, ProfessionalService, FavouriteService as FavService
from django.contrib import messages
from accounts.models import Address, ProfessionalProfile
from services.models import Service
from accounts.selectors import FavouriteSelector
from .selectors import DashboardSelector
# password change
from accounts.forms import LocalHubPasswordChangeForm
from django.contrib.auth import update_session_auth_hash


@login_required
def customer_dashboard(request):

    context = DashboardSelector.customer_dashboard(
        request.user,
    )

    return render(
        request,
        "dashboard/customer/dashboard.html",
        context,
    )

@login_required
def profile(request):
    password_form = LocalHubPasswordChangeForm(
        request.user,
    )
    if request.method == "POST":



        if password_form.is_valid():
            ProfileService.change_password(
                request,
                password_form,
            )

            messages.success(
                request,
                "Password updated successfully.",
            )

            return redirect(
                "customer_profile",
            )

    context = ProfileService.get_profile_context(
        request.user,
    )

    context["default_address"] = Address.objects.filter(
        user=request.user,
        is_default=True,
        is_active=True,
    ).first()

    context["has_professional_profile"] = (
        ProfessionalService.has_profile(
            request.user,
        )
    )
    return render(
        request,
        "dashboard/customer/profile.html",
        context,
    )

@login_required
def edit_profile(request):
    if request.method == "POST":
        success, form = ProfileService.update_profile(
            request.user,
            request,
        )
        if success:
            messages.success(request,"Profile updated successfully.",)
            return redirect("customer_profile")
    else:
        form = ProfileService.get_profile_form(request.user)
        return render(request, "dashboard/customer/edit_profile.html",{
            "form": form, },)

# @login_required
# def change_password(request):
#     if request.method == "POST":
#         form = LocalHubPasswordChangeForm(
#             request.user, request.POST,
#         )
#         if form.is_valid():
#             form.save()
#             update_session_auth_hash(
#                 request, form.user
#             )
#             messages.success(request,"Password changed successfully.",)
#             return redirect("customer_profile")
#     else:
#         form =LocalHubPasswordChangeForm(request.user)
#     return render(request, "dashboard/customer/change_password.html",{"form":form},)

# DUMMY ___________


@login_required
def addresses(request):
    context ={
        "addresses": AddressService.list(
            request.user
        )
    }
    return render(request, "dashboard/customer/addresses.html", context)

@login_required
def add_address(request):

    next_url = request.GET.get("next")

    if request.method == "POST":

        success, form = AddressService.create(
            request.user,
            request.POST,
        )

        if success:

            messages.success(
                request,
                "Address added successfully.",
            )

            next_url = request.POST.get("next")

            if next_url:
                return redirect(next_url)

            return redirect("customer_addresses")

    else:

        form = AddressService.get_form()

    return render(
        request,
        "dashboard/customer/add_address.html",
        {
            "form": form,
            "next": next_url,
        },
    )
@login_required
def edit_address(request, pk):

    if request.method == "POST":

        success, form = AddressService.update(
            request.user,
            pk,
            request.POST,
        )

        if success:

            messages.success(
                request,
                "Address updated successfully."
            )

            return redirect("customer_addresses")

    else:

        address, form = AddressService.get_address_form(
            request.user,
            pk,
        )

    return render(
        request,
        "dashboard/customer/edit_address.html",
        {
            "form": form,
        },
    )

@login_required
def make_default_address(request,pk):
    AddressService.make_default(
        request.user,
        pk,
    )
    messages.success(request, "Default address updated.")
    return redirect("customer_addresses")

@login_required
def delete_address(request, pk):

    AddressService.delete(
        request.user,
        pk,
    )

    messages.success(
        request,
        "Address deleted."
    )

    return redirect("customer_addresses")

@login_required
def bookings(request):
    return render(request, "dashboard/customer/bookings.html")


@login_required
def tasks(request):
    return render(request, "dashboard/customer/tasks.html")


@login_required
def notifications(request):
    return render(request, "dashboard/customer/notifications.html")


@login_required
def favourite_services(request):
    favs = FavouriteSelector.user_favourite_services(request.user)
    return render(
        request,
        "dashboard/customer/favourite_services.html",
        {"favourites": favs},
    )


@login_required
def favourite_professionals(request):
    favs = FavouriteSelector.user_favourite_professionals(request.user)
    return render(
        request,
        "dashboard/customer/favourite_professionals.html",
        {"favourites": favs},
    )


@login_required
def toggle_favourite_service(request, service_id):
    if request.method == "POST":
        service = get_object_or_404(Service, id=service_id)
        is_fav = FavService.toggle_service_favourite(request.user, service)
        return JsonResponse({"status": "success", "is_favourited": is_fav})
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)


@login_required
def toggle_favourite_professional(request, professional_id):
    if request.method == "POST":
        professional = get_object_or_404(ProfessionalProfile, id=professional_id)
        is_fav = FavService.toggle_professional_favourite(request.user, professional)
        return JsonResponse({"status": "success", "is_favourited": is_fav})
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)