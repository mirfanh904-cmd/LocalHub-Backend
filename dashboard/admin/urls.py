from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="admin_dashboard"),

    # Service Group Management
    path("groups/", views.service_group_list, name="admin_service_group_list"),
    path("groups/create/", views.service_group_create, name="admin_service_group_create"),
    path("groups/<int:pk>/edit/", views.service_group_edit, name="admin_service_group_edit"),
    path("groups/<int:pk>/delete/", views.service_group_delete, name="admin_service_group_delete"),
    path("groups/<int:pk>/toggle-active/", views.service_group_toggle_active, name="admin_service_group_toggle_active"),

    # Category Management
    path("categories/", views.category_list, name="admin_category_list"),
    path("categories/create/", views.category_create, name="admin_category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="admin_category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="admin_category_delete"),
    path("categories/<int:pk>/toggle-active/", views.category_toggle_active, name="admin_category_toggle_active"),
    path("categories/<int:pk>/toggle-featured/", views.category_toggle_featured, name="admin_category_toggle_featured"),
    path("categories/bulk-action/", views.category_bulk_action, name="admin_category_bulk_action"),

    # Service Management
    path("services/", views.service_list, name="admin_service_list"),
    path("services/create/", views.service_create, name="admin_service_create"),
    path("services/<int:pk>/edit/", views.service_edit, name="admin_service_edit"),
    path("services/<int:pk>/delete/", views.service_delete, name="admin_service_delete"),
    path("services/<int:pk>/toggle-active/", views.service_toggle_active, name="admin_service_toggle_active"),
    path("services/<int:pk>/toggle-featured/", views.service_toggle_featured, name="admin_service_toggle_featured"),

    # Service Package CRUD
    path("services/<int:service_pk>/packages/add/", views.package_create, name="admin_package_create"),
    path("services/<int:service_pk>/packages/<int:pk>/edit/", views.package_edit, name="admin_package_edit"),
    path("services/<int:service_pk>/packages/<int:pk>/delete/", views.package_delete, name="admin_package_delete"),

    # Service FAQ CRUD
    path("services/<int:service_pk>/faqs/add/", views.faq_create, name="admin_faq_create"),
    path("services/<int:service_pk>/faqs/<int:pk>/edit/", views.faq_edit, name="admin_faq_edit"),
    path("services/<int:service_pk>/faqs/<int:pk>/delete/", views.faq_delete, name="admin_faq_delete"),

    # Service Requirement CRUD
    path("services/<int:service_pk>/requirements/add/", views.requirement_create, name="admin_requirement_create"),
    path("services/<int:service_pk>/requirements/<int:pk>/edit/", views.requirement_edit, name="admin_requirement_edit"),
    path("services/<int:service_pk>/requirements/<int:pk>/delete/", views.requirement_delete, name="admin_requirement_delete"),

    # Professional Management
    path("professionals/", views.professional_list, name="admin_professional_list"),
    path("professionals/<str:pk>/", views.professional_detail, name="admin_professional_detail"),
    path("professionals/<str:pk>/approve/", views.approve_professional, name="admin_approve_professional"),
    path("professionals/<str:pk>/reject/", views.reject_professional, name="admin_reject_professional"),

    # Customer Management
    path("customers/", views.customer_list, name="admin_customer_list"),
    path("customers/<str:pk>/", views.customer_detail, name="admin_customer_detail"),

    # Booking Management
    path("bookings/", views.booking_list, name="admin_booking_list"),
    path("bookings/<str:booking_number>/", views.booking_detail, name="admin_booking_detail"),
    path("bookings/<str:booking_number>/assign/", views.booking_assign_worker, name="admin_booking_assign_worker"),
    path("bookings/<str:booking_number>/override-status/", views.booking_override_status, name="admin_booking_override_status"),
    path("bookings/<str:booking_number>/cancel/", views.booking_cancel, name="admin_booking_cancel"),
]