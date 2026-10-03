from django.urls import path, include
from . import views
from .settings import customer_settings
urlpatterns = [
    path("customer/", views.customer_dashboard, name="customer_dashboard"),
    path("customer/profile/", views.profile, name="customer_profile"),
    path("customer/profile/edit/", views.edit_profile, name="edit_profile"),
    path("customer/bookings/", views.bookings, name="customer_bookings"),
    path("customer/tasks/", views.tasks, name="customer_tasks"),
    path("customer/addresses/", views.addresses, name="customer_addresses"),
    path("customer/addresses/add/", views.add_address, name="add_address"),
    path("customer/addresses/<int:pk>/edit/", views.edit_address, name="edit_address"),
    path("customer/addresses/<int:pk>/default/", views.make_default_address, name="make_default_address", ),
    path("customer/addresses/<int:pk>/delete/", views.delete_address, name="delete_address", ),

    path("customer/notifications/", views.notifications, name="customer_notifications"),
    path("customer/settings/", customer_settings, name="customer_settings"),

    path("customer/favourites/services/", views.favourite_services, name="customer_favourite_services"),
    path("customer/favourites/professionals/", views.favourite_professionals, name="customer_favourite_professionals"),
    path("customer/favourites/services/<int:service_id>/toggle/", views.toggle_favourite_service, name="toggle_favourite_service"),
    path("customer/favourites/professionals/<int:professional_id>/toggle/", views.toggle_favourite_professional, name="toggle_favourite_professional"),

    path("professional/", include("dashboard.professional.urls"),),
    path("admin/", include("dashboard.admin.urls"))
]