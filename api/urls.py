from django.urls import include, path

urlpatterns = [
    # Authentication & Accounts
    path("v1/auth/", include("api.v1.auth.urls")),
    path("v1/accounts/", include("api.v1.accounts.urls")),

    # Catalog & Professionals
    path("v1/service-groups/", include("api.v1.service_groups.urls")),
    path("v1/categories/", include("api.v1.categories.urls")),
    path("v1/category/", include("api.v1.category.urls")),  # alias
    path("v1/services/", include("api.v1.services.urls")),
    path("v1/professionals/", include("api.v1.professionals.urls")),

    # Bookings & Reviews
    path("v1/bookings/", include("api.v1.bookings.urls")),
    path("v1/reviews/", include("api.v1.reviews.urls")),

    # Task Marketplace (Phase 4)
    path("v1/tasks/", include("api.v1.tasks.urls")),
    path("v1/task-categories/", include("api.v1.tasks.urls")),

    # Healthcare Ecosystem (Phase 6)
    path("v1/healthcare/", include("api.v1.healthcare.urls")),

    # Trust & Safety
    path("v1/verification/", include("api.v1.verification.urls")),
    path("v1/complaints/", include("api.v1.complaints.urls")),

    # Worker & Customer Auxiliaries
    path("v1/worker/", include("api.v1.worker.urls")),
    path("v1/notifications/", include("api.v1.notifications.urls")),
    path("v1/favourites/", include("api.v1.favourites.urls")),

    # Payments & Wallet Ecosystem (Phase 7)
    path("v1/payments/", include("api.v1.payments.urls")),

    # Administration
    path("v1/admin/", include("api.v1.admin.urls")),
]