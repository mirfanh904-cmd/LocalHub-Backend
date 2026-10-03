from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserProfile, Skill, Language, ProfessionalProfile, ProfessionalService, FavouriteService, FavouriteProfessional


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("-created_at",)
    list_display = (
        "email",
        "full_name",
        "phone",
        "role",
        "is_email_verified",
        "is_phone_verified",
        "profile_completed",
        "is_active",
        "created_at",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_email_verified",
        "is_phone_verified",
        "profile_completed",
        "login_provider",
        "created_at",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_seen",
        "deleted_at",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "id",
                    "email",
                    "phone",
                    "password",
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Role",
            {
                "fields": (
                    "role",
                    "login_provider",
                )
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "is_email_verified",
                    "is_phone_verified",
                    "profile_completed",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Activity",
            {
                "fields": (
                    "last_seen",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Soft Delete",
            {
                "fields": (
                    "is_deleted",
                    "deleted_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "role",
                ),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "gender",
        "date_of_birth",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(Skill)
admin.site.register(Language)
admin.site.register(ProfessionalProfile)
@admin.register(ProfessionalService)
class ProfessionalServiceAdmin(admin.ModelAdmin):

    list_display = (
        "professional",
        "service",
        "custom_price",
        "is_active",
        "is_featured",
    )

    list_filter = (
        "is_active",
        "is_featured",
        "service",
    )

    search_fields = (
        "professional__user__full_name",
        "service__name",
    )


admin.site.register(FavouriteService)
admin.site.register(FavouriteProfessional)