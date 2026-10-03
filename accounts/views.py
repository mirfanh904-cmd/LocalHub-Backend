from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.services import ProfessionalService
from .forms import RegisterForm, LoginForm
from .services import AuthService
from django.utils.http import url_has_allowed_host_and_scheme

def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            AuthService.register_user(form.cleaned_data)

            messages.success(
                request,
                "Registration completed successfully."
            )

            return redirect("login")

    else:

        form = RegisterForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "accounts/register.html",
        context,
    )


def login_view(request):

    if request.user.is_authenticated:
        return redirect("customer_dashboard")

    if request.method == "POST":

        form = LoginForm(request.POST)

        if form.is_valid():

            user = AuthService.login_user(
                request,
                form.cleaned_data
            )

            if user:

                messages.success(
                    request,
                    "Welcome back!"
                )

                next_url = request.GET.get("next")

                if next_url and url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={request.get_host()},):
                    return redirect(next_url)

                if user.is_superuser:

                    return redirect(
                        "admin_dashboard",
                    )

                elif ProfessionalService.has_profile(user=user):

                    return redirect(
                        "professional_dashboard",
                    )

                return redirect(
                    "home",
                )
            messages.error(
                request,
                "Invalid email or password."
            )

    else:

        form = LoginForm()

    context = {
        "form": form
    }

    return render(
        request,
        "accounts/login.html",
        context
    )


def logout_view(request):
    AuthService.logout_user(request)
    messages.success(
        request,
        "You have been logged out successfully."
    )
    return redirect("home")

