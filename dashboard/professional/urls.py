from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.professional_dashboard,
        name="professional_dashboard",
    ),
    path(
        "profile/edit/",
        views.edit_professional_profile,
        name="edit_professional_profile",
    ),
    path("profile/",views.professional_profile,name="professional_profile",),
    path(
        "bookings/<str:booking_number>/",
        views.professional_booking_detail,
        name="professional_booking_detail",
    ),
    path(
        "bookings/<str:booking_number>/accept/",
        views.accept_booking,
        name="professional_accept_booking",
    ),
    path(
        "bookings/<str:booking_number>/reject/",
        views.reject_booking,
        name="professional_reject_booking",
    ),
    path(
        "bookings/<str:booking_number>/update-status/",
        views.update_booking_status,
        name="professional_update_booking_status",
    ),
]