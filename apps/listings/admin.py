from django.contrib import admin

from apps.listings.models import Category, Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    fields = ("image_key", "order")
    ordering = ("order",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "icon")
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "seller",
        "category",
        "price",
        "condition",
        "status",
        "is_negotiable",
        "views_count",
        "created_at",
    )
    list_filter = (
        "status",
        "condition",
        "is_negotiable",
        "accepts_meetup",
        "accepts_delivery",
        "category",
    )
    search_fields = ("title", "description", "seller__shop_name")
    readonly_fields = ("views_count", "created_at", "updated_at")
    inlines = [ListingImageInline]
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return Listing.all_objects.all()


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ("listing", "image_key", "order")
    list_filter = ("listing",)
    search_fields = ("listing__title", "image_key")
    ordering = ("listing", "order")
