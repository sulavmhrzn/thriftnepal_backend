from django.contrib import admin

from apps.profiles.models import SellerProfile, SellerSocialLink


class SellerSocialLinkInline(admin.TabularInline):
    model = SellerSocialLink
    extra = 0
    fields = ("platform", "url")


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "shop_name",
        "user",
        "province",
        "district",
        "is_verified_seller",
        "government_id_verified",
        "is_active",
        "total_listings",
        "total_sales",
        "average_rating",
        "created_at",
    )
    list_filter = (
        "is_verified_seller",
        "government_id_verified",
        "is_active",
        "accepts_meetup",
        "accepts_delivery",
        "province",
    )
    search_fields = ("shop_name", "slug", "user__email", "phone_number")
    readonly_fields = (
        "slug",
        "average_rating",
        "total_reviews",
        "total_sales",
        "total_listings",
        "verified_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Shop",
            {
                "fields": (
                    "user",
                    "shop_name",
                    "slug",
                    "bio",
                    "phone_number",
                    "profile_picture",
                    "banner_image",
                )
            },
        ),
        (
            "Location",
            {"fields": ("province", "district", "city", "landmark")},
        ),
        (
            "Verification",
            {
                "fields": (
                    "is_verified_seller",
                    "verified_at",
                    "government_id_key",
                    "government_id_verified",
                )
            },
        ),
        (
            "Preferences",
            {
                "fields": (
                    "is_active",
                    "accepts_meetup",
                    "accepts_delivery",
                )
            },
        ),
        (
            "Stats",
            {
                "fields": (
                    "average_rating",
                    "total_reviews",
                    "total_sales",
                    "total_listings",
                )
            },
        ),
        (
            "SEO",
            {"fields": ("meta_title", "meta_description")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    inlines = [SellerSocialLinkInline]


@admin.register(SellerSocialLink)
class SellerSocialLinkAdmin(admin.ModelAdmin):
    list_display = ("seller", "platform", "url")
    list_filter = ("platform",)
    search_fields = ("seller__shop_name", "url")
    autocomplete_fields = ("seller",)
