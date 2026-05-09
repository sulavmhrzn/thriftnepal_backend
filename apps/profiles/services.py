import structlog
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.minio import delete_file, upload_file
from apps.core.utils import generate_unique_slug
from apps.profiles.models import SellerProfile, SellerSocialLink

logger = structlog.get_logger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def update_seller_profile(seller, data):
    with transaction.atomic():
        for field, value in data.items():
            if field == "shop_name" and value != seller.shop_name:
                seller.slug = generate_unique_slug(value, SellerProfile)

            setattr(seller, field, value)
        seller.save()
    logger.info(
        "seller_profile_updated",
        seller_id=str(seller.id),
        user_id=str(seller.user.id),
        updated_fields=list(data.keys()),
    )
    return seller


def update_social_links(seller, data):
    with transaction.atomic():
        SellerSocialLink.objects.filter(seller=seller).delete()
        if not data:
            logger.info("social_links_cleared", seller_id=str(seller.id))
            return []
        new_links = SellerSocialLink.objects.bulk_create(
            [
                SellerSocialLink(
                    seller=seller, platform=link["platform"], url=link["url"]
                )
                for link in data
            ]
        )
        logger.info(
            "social_links_updated",
            seller_id=str(seller.id),
            link_count=len(new_links),
            platforms=[link["platform"] for link in data],
        )

        return new_links


def _validate_file(file, allowed_types: set, max_size: int) -> None:
    if file.content_type not in allowed_types:
        raise ValidationError(
            {"file": [f"Unsupported file type. Allowed: {', '.join(allowed_types)}"]}
        )
    if file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            {"file": [f"File too large. Maximum size is {max_mb:.0f}MB."]}
        )


def upload_profile_picture(seller: SellerProfile, file) -> SellerProfile:
    _validate_file(file, ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE)

    if seller.profile_picture:
        delete_file(seller.profile_picture, private=False)

    key = upload_file(
        file=file,
        prefix=f"seller-profiles/{seller.id}/profile",
        content_type=file.content_type,
        private=False,
    )

    seller.profile_picture = key
    seller.save(update_fields=["profile_picture", "updated_at"])

    logger.info("profile_picture_uploaded", seller_id=str(seller.id), key=key)
    return seller


def upload_banner_image(seller: SellerProfile, file) -> SellerProfile:
    _validate_file(file, ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE)

    if seller.banner_image:
        delete_file(seller.banner_image, private=False)

    key = upload_file(
        file=file,
        prefix=f"seller-profiles/{seller.id}/banner",
        content_type=file.content_type,
        private=False,
    )

    seller.banner_image = key
    seller.save(update_fields=["banner_image", "updated_at"])

    logger.info("banner_image_uploaded", seller_id=str(seller.id), key=key)
    return seller


def upload_government_id(seller: SellerProfile, file) -> SellerProfile:
    _validate_file(file, ALLOWED_DOCUMENT_TYPES, MAX_DOCUMENT_SIZE)

    if seller.government_id_key:
        delete_file(seller.government_id_key, private=True)

    key = upload_file(
        file=file,
        prefix=f"seller-profiles/{seller.id}/government-id",
        content_type=file.content_type,
        private=True,
    )

    seller.government_id_key = key
    seller.government_id_verified = False
    seller.save(
        update_fields=[
            "government_id_key",
            "government_id_verified",
            "updated_at",
        ]
    )
    logger.info("government_id_uploaded", seller_id=str(seller.id))
    return seller
