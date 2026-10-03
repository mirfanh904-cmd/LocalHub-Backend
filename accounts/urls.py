from django.urls import path
from .views import register, login_view, logout_view
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

# app_name = "accounts"

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login_view, name='login'),
    path("logout/", logout_view, name='logout'),



    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/forgot_password.html",
            email_template_name="accounts/emails/password_reset_email.html",
            subject_template_name="accounts/emails/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="forgot_password",
    ),
    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]

