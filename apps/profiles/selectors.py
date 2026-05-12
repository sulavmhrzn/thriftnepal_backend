import structlog
from rest_framework.exceptions import NotFound

from apps.profiles.models import BuyerProfile, SellerProfile, SellerSocialLink

logger = structlog.get_logger(__name__)


def get_seller_profile_by_user(user) -> SellerProfile:
    try:
        return SellerProfile.objects.select_related("user").get(user=user)
    except SellerProfile.DoesNotExist:
        raise NotFound("Seller profile not found.")


def get_seller_profile_by_id(profile_id) -> SellerProfile:
    try:
        return SellerProfile.objects.select_related("user").get(id=profile_id)
    except SellerProfile.DoesNotExist:
        raise NotFound("Seller profile not found.")


def get_seller_profile_by_slug(slug: str) -> SellerProfile:
    try:
        return (
            SellerProfile.objects.select_related("user")
            .prefetch_related("social_links")
            .get(slug=slug)
        )
    except SellerProfile.DoesNotExist:
        raise NotFound("No shop found with this name.")


def get_top_rated_sellers(limit: int = 10) -> list[SellerProfile]:
    return (
        SellerProfile.objects.select_related("user")
        .filter(
            is_active=True,
            is_verified_seller=True,
        )
        .order_by("-average_rating")[:limit]
    )


def get_all_active_sellers() -> list[SellerProfile]:
    return (
        SellerProfile.objects.select_related("user")
        .filter(is_active=True)
        .order_by("-average_rating")
    )


def get_social_links_by_seller(seller: SellerProfile) -> list[SellerSocialLink]:
    return SellerSocialLink.objects.filter(seller=seller).order_by("platform")


def get_buyer_profile_by_user(user) -> BuyerProfile:
    try:
        return BuyerProfile.objects.select_related("user").get(user=user)
    except BuyerProfile.DoesNotExist:
        raise NotFound("Buyer profile not found.")


def get_buyer_profile_by_id(profile_id) -> BuyerProfile:
    try:
        return BuyerProfile.objects.select_related("user").get(id=profile_id)
    except BuyerProfile.DoesNotExist:
        raise NotFound("Buyer profile not found.")
