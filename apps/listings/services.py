import structlog
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from apps.audits.services import create_business_event
from apps.core.minio import delete_file, upload_file
from apps.listings.enums import ListingStatus
from apps.listings.models import Listing, ListingImage
from apps.listings.selectors import get_category_by_id, get_listing_image_count
from apps.profiles.models import SavedListing, SellerProfile

logger = structlog.get_logger(__name__)

MAX_IMAGES_PER_LISTING = 8
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def create_listing(seller: SellerProfile, data: dict) -> Listing:
    """Creates listing in draft status"""

    category = get_category_by_id(data.pop("category_id"))

    listing = Listing.all_objects.create(
        seller=seller,
        category=category,
        status=ListingStatus.DRAFT,
        **data,
    )

    logger.info(
        "listing_created",
        listing_id=str(listing.id),
        seller_id=str(seller.id),
    )

    return listing


def update_listing(listing: Listing, data: dict) -> Listing:
    protected_fields = {"seller", "status", "views_count"}
    if listing.status == ListingStatus.SOLD:
        raise ValidationError({"non_field_errors": ["Sold listings cannot be updated"]})

    if listing.status == ListingStatus.ARCHIVED:
        raise ValidationError(
            {
                "non_field_errors": [
                    "Archived listings cannot be updated. Reactive first."
                ]
            }
        )

    with transaction.atomic():
        for field, value in data.items():
            if field in protected_fields:
                continue

            if field == "category_id":
                listing.category = get_category_by_id(value)
                continue

            setattr(listing, field, value)
        listing.save()

    logger.info(
        "listing_updated",
        listing_id=str(listing.id),
        updated_fields=list(data.keys()),
    )

    return listing


def soft_delete_listing(listing: Listing, request=None):
    with transaction.atomic():
        listing.is_deleted = True
        listing.save_count = 0
        listing.save(update_fields=["is_deleted", "save_count", "updated_at"])
        ListingImage.objects.filter(listing=listing).update(is_deleted=True)
        SavedListing.objects.filter(listing=listing).delete()

    create_business_event(
        action="listing_deleted",
        user=listing.seller.user,
        metadata={"listing_id": str(listing.id), "title": listing.title},
        request=request,
    )
    logger.info(
        "listing_soft_deleted",
        listing_id=str(listing.id),
        seller_id=str(listing.seller.id),
    )


def publish_listing(listing: Listing) -> Listing:
    if listing.status != ListingStatus.DRAFT:
        raise ValidationError(
            {
                "non_field_errors": [
                    f"Only draft listings can be published. Current status: {listing.status}"
                ]
            }
        )

    image_count = get_listing_image_count(listing)
    if image_count == 0:
        raise ValidationError(
            {
                "non_field_errors": [
                    "Listing must have at least on image before publishing"
                ]
            }
        )

    listing.status = ListingStatus.ACTIVE
    listing.save(update_fields=("status", "updated_at"))

    logger.info(
        "listing_published",
        listing_id=str(listing.id),
        seller_id=str(listing.seller.id),
    )
    return listing


def mark_listing_as_sold(listing: Listing, request=None) -> Listing:
    if listing.status != ListingStatus.ACTIVE:
        raise ValidationError(
            {"non_field_errors": ["Only active listings can be marked as sold"]}
        )

    with transaction.atomic():
        listing.status = ListingStatus.SOLD
        listing.save(update_fields=["status", "updated_at"])
        listing.seller.total_sales += 1
        listing.seller.save(update_fields=["total_sales", "updated_at"])

    create_business_event(
        action="listing_marked_sold",
        user=listing.seller.user,
        metadata={"listing_id": str(listing.id), "title": listing.title},
        request=request,
    )

    logger.info(
        "listing_marked_sold",
        listing_id=str(listing.id),
        seller_id=str(listing.seller.id),
    )
    return listing


def archive_listing(listing: Listing) -> Listing:
    if listing.status not in {ListingStatus.ACTIVE, ListingStatus.DRAFT}:
        raise ValidationError(
            {"non_field_errors": ["Only active or draft listings can be archived"]}
        )

    listing.status = ListingStatus.ARCHIVED
    listing.save(update_fields=["status", "updated_at"])

    logger.info("listing_archived", listing_id=str(listing.id))
    return listing


def reactivate_listing(listing: Listing) -> Listing:
    if listing.status != ListingStatus.ARCHIVED:
        raise ValidationError(
            {"non_field_errors": ["Only archived listings can be reactivated"]}
        )

    listing.status = ListingStatus.ACTIVE
    listing.save(update_fields=["status", "updated_at"])

    logger.info("listing_reactivated", listing_id=str(listing.id))
    return listing


def increment_views_count(listing: Listing):
    Listing.all_objects.filter(id=listing.id).update(views_count=F("views_count") + 1)


def _validate_image(file) -> None:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            {"file": ["Unsupported file type. Allowed: jpeg, png, webp."]}
        )

    if file.size > MAX_IMAGE_SIZE:
        raise ValidationError({"file": ["Image too large. Maximum size is 5MB."]})


def upload_listing_image(listing: Listing, file) -> ListingImage:
    _validate_image(file)

    if listing.status in {ListingStatus.SOLD, ListingStatus.ARCHIVED}:
        raise ValidationError(
            {"non_field_errors": ["Cannot upload images to sold or archived listing"]}
        )

    current_count = get_listing_image_count(listing)
    if current_count >= MAX_IMAGES_PER_LISTING:
        raise ValidationError(
            {
                "non_field_errors": [
                    f"Maximum {MAX_IMAGES_PER_LISTING} images allowed per listing."
                ]
            }
        )
    key = upload_file(
        file=file,
        prefix=f"listings/{listing.id}",
        content_type=file.content_type,
        private=False,
    )

    image = ListingImage.objects.create(
        listing=listing,
        image_key=key,
        order=current_count,
    )

    logger.info(
        "listing_image_uploaded",
        listing_id=str(listing.id),
        image_id=str(image.id),
        order=image.order,
    )
    return image


def delete_listing_image(image: ListingImage):
    listing = image.listing
    deleted_order = image.order

    image_count = get_listing_image_count(listing)

    if listing.status == ListingStatus.ACTIVE and image_count <= 1:
        raise ValidationError(
            {
                "non_field_errors": [
                    "Cannot delete the last image of an active listing."
                    "Archive the listing first or upload another image."
                ]
            }
        )

    with transaction.atomic():
        delete_file(image.image_key, private=False)
        image.delete()

        remaining = ListingImage.objects.filter(
            listing=listing, order__gt=deleted_order
        )
        for img in remaining:
            img.order -= 1
            img.save(update_fields=["order"])
    logger.info(
        "listing_image_deleted",
        listing_id=str(listing.id),
        deleted_order=deleted_order,
    )


def reorder_listing_images(listing: Listing, image_ids: list) -> list[ListingImage]:
    images = ListingImage.objects.filter(listing=listing)
    existing_ids = set(str(img.id) for img in images)
    provided_ids = set(str(i) for i in image_ids)

    if len(image_ids) != len(set(str(i) for i in image_ids)):
        raise ValidationError({"non_field_errors": ["Duplicate image IDs not allowed"]})

    if existing_ids != provided_ids:
        raise ValidationError(
            {
                "non_field_errors": [
                    "All listing image IDs must be provided for reordering"
                ]
            }
        )

    with transaction.atomic():
        image_map = {str(img.id): img for img in images}
        images_to_update = []

        for order, image_id in enumerate(image_ids):
            img = image_map[str(image_id)]
            img.order = order
            images_to_update.append(img)

        ListingImage.objects.bulk_update(images_to_update, ["order"])

    return list(ListingImage.objects.filter(listing=listing).order_by("order"))
