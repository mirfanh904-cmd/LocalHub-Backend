from django.contrib import admin
from .models import ProfessionalVerification, ProfessionalVerificationDocument


class ProfessionalVerificationDocumentInline(admin.TabularInline):
    model = ProfessionalVerificationDocument
    extra = 0
    fields = (
        "document_type",
        "document_number",
        "status",
        "document_file",
        "ocr_success",
    )
    readonly_fields = ("ocr_success",)
    show_change_link = True


@admin.register(ProfessionalVerification)
class ProfessionalVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "professional",
        "status",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "submitted_at",
        "created_at",
    )

    search_fields = (
        "professional__user__first_name",
        "professional__user__last_name",
        "professional__user__email",
        "professional__user__phone",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "submitted_at",
        "reviewed_at",
    )

    inlines = [ProfessionalVerificationDocumentInline]


@admin.register(ProfessionalVerificationDocument)
class ProfessionalVerificationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "verification",
        "document_type",
        "status",
        "ocr_success",
        "created_at",
    )

    list_filter = (
        "document_type",
        "status",
        "ocr_success",
    )

    search_fields = (
        "document_number",
        "verification__professional__user__first_name",
        "verification__professional__user__last_name",
        "verification__professional__user__email",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "ocr_name",
        "ocr_document_number",
        "ocr_date_of_birth",
        "ocr_expiry_date",
        "ocr_raw_text",
        "ocr_processed_at",
        "ocr_success",
        "ocr_error",
        "created_at",
        "updated_at",
    )