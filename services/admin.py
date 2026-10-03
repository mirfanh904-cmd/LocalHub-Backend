from django.contrib import admin
from django.utils.html import format_html

from .models import ServiceGroup, Category, Service,\
    ServicePackage, ServicePackageInclude,\
    ServiceRequirement, ServiceFAQ

class ServicePackageInline(admin.TabularInline):
    model = ServicePackage
    extra = 1

    fields = (
        "name",
        "price",
        "duration",
        "sort_order",
        "is_popular",
        "is_active",
    )

    ordering = ("sort_order",)
@admin.register(ServiceGroup)
class ServiceGroupAdmin(admin.ModelAdmin):

    list_display = (
        "display_order",
        "name",
        "group_icon",
        "featured",
        "is_active",
        "created_at",
    )

    list_display_links = (
        "name",
    )

    list_editable = (
        "display_order",
        "is_active",
    )

    search_fields = (
        "name",
        "short_description",
    )

    list_filter = (
        "is_active",
        "is_featured",
        "created_at",
    )

    ordering = (
        "display_order",
        "name",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    readonly_fields = (
        "created_at",
        "updated_at",
        "deleted_at",
        "preview_cover",

    )

    fieldsets = (

        ("Basic Information", {
            "fields": (
                "name",
                "slug",
                "short_description",
                "description",
            )
        }),

        ("Media", {
            "fields": (
                "icon_class",
                "cover_image",
                "preview_cover",
            )
        }),

        ("Appearance", {
            "fields": (
                "theme_color",
                "display_order",
            )
        }),

        ("SEO", {
            "classes": ("collapse",),
            "fields": (
                "seo_title",
                "seo_description",
            )
        }),

        ("Status", {
            "fields": (
                "is_featured",
                "is_active",
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

    @admin.display(description="Icon")
    def group_icon(self, obj):

        return format_html(
            '<i class="bi {}" style="font-size:24px;color:{};"></i>',
            obj.icon_class or "bi-grid",
            obj.theme_color or "#2563EB",
        )

    @admin.display(boolean=True)
    def featured(self, obj):

        return obj.is_featured

    def preview_cover(self, obj):

        if obj.cover_image:

            return format_html(
                '<img src="{}" width="250" style="border-radius:12px;">',
                obj.cover_image.url
            )

        return "No Image"

    preview_cover.short_description = "Cover Preview"



    class Media:

        css = {

            "all": (

                "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css",

            )

        }

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "display_order",
        "name",
        "service_group",
        "category_icon",
        "featured",
        "is_active",
        "created_at",
    )

    list_display_links = (
        "name",
    )

    list_editable = (
        "display_order",
        "is_active",
    )

    search_fields = (
        "name",
        "short_description",
        "service_group__name",
    )

    list_filter = (
        "service_group",
        "is_featured",
        "is_active",
        "created_at",
    )

    ordering = (
        "service_group",
        "display_order",
        "name",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    readonly_fields = (
        "preview_cover",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    fieldsets = (

        ("Basic Information", {
            "fields": (
                "service_group",
                "name",
                "slug",
                "short_description",
                "description",
            )
        }),

        ("Media", {
            "fields": (
                "bootstrap_icon",
                "cover_image",
                "preview_cover",
            )
        }),

        ("Appearance", {
            "fields": (
                "theme_color",
                "display_order",
            )
        }),

        ("SEO", {
            "classes": ("collapse",),
            "fields": (
                "seo_title",
                "seo_description",
            )
        }),

        ("Status", {
            "fields": (
                "is_featured",
                "is_active",
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

    @admin.display(description="Icon")
    def category_icon(self, obj):
        return format_html(
            '<i class="bi {}" style="font-size:24px;color:{};"></i>',
            obj.bootstrap_icon or "bi-grid",
            obj.theme_color or "#2563EB",
        )

    @admin.display(boolean=True)
    def featured(self, obj):
        return obj.is_featured

    def preview_cover(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="250" style="border-radius:12px;">',
                obj.cover_image.url
            )

        return "No Image"

    preview_cover.short_description = "Cover Preview"

    class Media:
        css = {

            "all": (

                "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css",

            )

        }
class ServiceRequirementInline(admin.TabularInline):
    model = ServiceRequirement
    extra = 1

    fields = (
        "label",
        "field_name",
        "field_type",
        "required",
        "sort_order",
        "is_active",
    )


class ServicePackageIncludeInline(admin.TabularInline):
    model=ServicePackageInclude
    extra=1
    fields=("title","icon","sort_order")

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    inlines = [
        ServicePackageInline,
        ServiceRequirementInline,
    ]
    list_display = (
        "display_order",
        "name",
        "category",
        "starting_price",
        "featured",
        "is_active",
        "created_at",
    )

    list_display_links = (
        "name",
    )

    list_editable = (
        "display_order",
        "is_active",
    )

    search_fields = (
        "name",
        "category__name",
        "category__service_group__name",
    )

    list_filter = (
        "category__service_group",
        "category",
        "is_featured",
        "is_active",
        "created_at",
    )

    ordering = (
        "category",
        "display_order",
        "name",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    readonly_fields = (
        "preview_cover",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    fieldsets = (

        ("Basic Information", {
            "fields": (
                "category",
                "name",
                "slug",
                "short_description",
                "description",
            )
        }),

        ("Media", {
            "fields": (
                "icon_class",
                "cover_image",
                "preview_cover",
            )
        }),

        ("Pricing", {
            "fields": (
                "starting_price",
                "estimated_duration",
            )
        }),

        ("Appearance", {
            "fields": (
                "theme_color",
                "display_order",
            )
        }),

        ("SEO", {
            "classes": ("collapse",),
            "fields": (
                "seo_title",
                "seo_description",
            )
        }),

        ("Status", {
            "fields": (
                "is_featured",
                "is_active",
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

    @admin.display(boolean=True)
    def featured(self, obj):
        return obj.is_featured

    def preview_cover(self, obj):

        if obj.cover_image:

            return format_html(
                '<img src="{}" width="250" style="border-radius:12px;">',
                obj.cover_image.url
            )

        return "No Image"

    preview_cover.short_description = "Cover Preview"

    class Media:

        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css",
            )
        }

@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display=("name","service","price","duration","is_popular","is_active")
    list_filter=("service","is_popular","is_active")
    search_fields=("name","service__name")
    list_editable=("is_popular","is_active")
    prepopulated_fields={"slug":("name",)}
    ordering=("service","sort_order")
    inlines=[ServicePackageIncludeInline]

@admin.register(ServicePackageInclude)
class ServicePackageIncludeAdmin(admin.ModelAdmin):
    list_display=("title","package","sort_order")
    list_filter=("package__service",)
    search_fields=("title","package__name")
    ordering=("package","sort_order")


    ordering = ("sort_order",)
@admin.register(ServiceRequirement)
class ServiceRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "service",
        "field_type",
        "required",
        "sort_order",
        "is_active",
    )

    list_filter = (
        "field_type",
        "required",
        "is_active",
    )

    search_fields = (
        "label",
        "field_name",
        "service__name",
    )

    ordering = (
        "service",
        "sort_order",
    )


@admin.register(ServiceFAQ)
class ServiceFAQAdmin(admin.ModelAdmin):
    list_display = ("question", "service", "sort_order", "is_active")
    list_filter = ("service", "is_active")
    search_fields = ("question", "answer", "service__name")
    ordering = ("service", "sort_order")