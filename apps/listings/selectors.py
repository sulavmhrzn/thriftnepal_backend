import structlog
from django.db.models import Count
from rest_framework.exceptions import NotFound

from apps.listings.models import Category, Listing, ListingImage
from apps.profiles.models import SellerProfile

logger = structlog.get_logger(__name__)


def get_all_categories() -> list[Category]:
    return (
        Category.objects.filter(parent__isnull=True)
        .prefetch_related("children")
        .order_by("name")
    )


def get_category_by_slug(slug: str) -> Category:
    try:
        return Category.objects.get(slug=slug)
    except Category.DoesNotExist:
        raise NotFound("Category not found")


def get_category_by_id(category_id) -> Category:
    try:
        return Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        raise NotFound("Category not found")


def get_listing_by_id(listing_id) -> Listing:
    try:
        return (
            Listing.objects.select_related(
                "seller",
                "seller__user",
                "category",
                "category__parent",
            )
            .prefetch_related("images")
            .get(id=listing_id)
        )
    except Listing.DoesNotExist:
        raise NotFound("Listing not found")


def get_active_listings(filters: dict = None) -> list[Listing]:
    filters = filters or {}
    qs = (
        Listing.objects.select_related(
            "seller",
            "seller__user",
            "category",
            "category__parent",
        )
        .prefetch_related("images")
        .annotate(image_count=Count("images"))
        .filter(image_count__gt=0)
    )

    if category_slug := filters.get("category_slug"):
        qs = qs.filter(category__slug=category_slug)

    if condition := filters.get("condition"):
        qs = qs.filter(condition=condition)

    if min_price := filters.get("min_price"):
        qs = qs.filter(price__gte=min_price)

    if max_price := filters.get("max_price"):
        qs = qs.filter(price__lte=max_price)

    if filters.get("is_negotiable") is not None:
        qs = qs.filter(is_negotiable=filters["is_negotiable"])

    if filters.get("accepts_meetup") is not None:
        qs = qs.filter(accepts_meetup=filters["accepts_meetup"])

    if filters.get("accepts_delivery") is not None:
        qs = qs.filter(accepts_delivery=filters["accepts_delivery"])

    if seller_id := filters.get("seller_id"):
        qs = qs.filter(seller__id=seller_id)

    return qs


def get_listing_by_id_for_seller(listing_id, seller: SellerProfile) -> Listing:
    try:
        return (
            Listing.all_objects.select_related(
                "seller",
                "seller__user",
                "category",
                "category__parent",
            )
            .prefetch_related("images")
            .get(id=listing_id, seller=seller)
        )
    except Listing.DoesNotExist:
        raise NotFound("Listing not found.")


def get_listings_by_seller(
    seller: SellerProfile,
    filters: dict = None,
) -> list[Listing]:
    filters = filters or {}

    qs = (
        Listing.all_objects.select_related("category", "category__parent")
        .prefetch_related("images")
        .filter(seller=seller, is_deleted=False)
    )

    if status := filters.get("status"):
        qs = qs.filter(status=status)

    return qs


def get_images_by_listing(listing: Listing) -> list[ListingImage]:
    return ListingImage.objects.filter(listing=listing).order_by("order")


def get_listing_image_count(listing: Listing) -> int:
    return ListingImage.objects.filter(listing=listing).count()


def get_listing_image_by_id(image_id, listing: Listing) -> ListingImage:
    try:
        return ListingImage.objects.get(id=image_id, listing=listing)
    except ListingImage.DoesNotExist:
        raise NotFound("Image not found")
