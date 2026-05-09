from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.utils import generate_unique_slug
from apps.profiles.models import SellerProfile
from apps.users.enums import UserRole
from apps.users.models import User


@receiver(post_save, sender=User)
def create_seller_profile(sender, instance, created, **kwargs):
    """
    Auto create SellerProfile when user role is seller.
    """

    if instance.role == UserRole.SELLER:
        if not SellerProfile.objects.filter(user=instance).exists():
            placeholder_name = f"shop_{str(instance.id)[:8]}"
            slug = generate_unique_slug(placeholder_name, SellerProfile)
            SellerProfile.objects.create(
                user=instance, shop_name=placeholder_name, slug=slug
            )
