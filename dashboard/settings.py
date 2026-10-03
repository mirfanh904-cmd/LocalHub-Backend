from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from accounts.forms import LocalHubPasswordChangeForm
from accounts.services import ProfileService
from django.contrib import messages


@login_required
def customer_settings(request):

    password_form = LocalHubPasswordChangeForm(
        request.user,
    )

    if request.method == "POST":

        password_form = LocalHubPasswordChangeForm(
            request.user,
            request.POST,
        )

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
                "customer_settings",
            )

    return render(
        request,
        "dashboard/customer/settings.html",
        {
            "password_form": password_form,
        },
    )