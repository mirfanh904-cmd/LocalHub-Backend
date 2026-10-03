from django.contrib import admin

from .models import Booking, BookingStatusHistory


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    list_display = (
        "booking_number",
        "customer",
        "service",
        "booking_date",
        "status",
        "payment_status",
        "total_amount",
        "created_at",
    )

    list_display_links = (
        "booking_number",
    )

    list_editable = (
        "status",
        "payment_status",
    )

    search_fields = (
        "booking_number",
        "customer__email",
        "customer__phone_number",
        "service__name",
    )

    list_filter = (
        "status",
        "payment_status",
        "booking_date",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "booking_number",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    fieldsets = (

        ("Booking Information", {
            "fields": (
                "booking_number",
                "customer",
                "worker",
                "service",
                "address",
            )
        }),

        ("Schedule", {
            "fields": (
                "booking_date",
                "start_time",
                "end_time",
            )
        }),

        ("Pricing", {
            "fields": (
                "subtotal",
                "discount",
                "platform_fee",
                "tax",
                "total_amount",
            )
        }),

        ("Status", {
            "fields": (
                "status",
                "payment_status",
            )
        }),

        ("Notes", {
            "fields": (
                "customer_note",
                "worker_note",
                "cancelled_reason",
            )
        }),

        ("Timeline", {
            "classes": ("collapse",),
            "fields": (
                "cancelled_at",
                "completed_at",
                "created_at",
                "updated_at",
                "deleted_at",
            )
        }),

    )


@admin.register(BookingStatusHistory)
class BookingStatusHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "booking",
        "status",
        "source",
        "changed_by",
        "created_at",
    )

    list_display_links = (
        "booking",
    )

    search_fields = (
        "booking__booking_number",
        "changed_by__email",
        "changed_by__phone_number",
    )

    list_filter = (
        "status",
        "source",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "deleted_at",
    )

    fieldsets = (

        ("Booking Status", {
            "fields": (
                "booking",
                "status",
                "source",
                "changed_by",
                "note",
            )
        }),

        ("System", {
            "classes": ("collapse",),
            "fields": (
                "created_at",
                "updated_at",
                "deleted_at",
            )
        }),

    )