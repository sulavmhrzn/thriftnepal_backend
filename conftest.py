import factory
from django.contrib.auth import get_user_model

from apps.profiles.enums import SocialPlatform
from apps.profiles.models import SellerProfile, SellerSocialLink
from apps.users.enums import UserRole

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    password = factory.django.Password("testpass123")
    role = UserRole.BUYER
    is_active = True
    is_verified = True


class SellerUserFactory(UserFactory):
    """Creates a User with SELLER role. The signal auto-creates SellerProfile."""

    role = UserRole.SELLER


class SellerProfileFactory(factory.django.DjangoModelFactory):
    """Creates a SellerProfile directly (bypassing the signal)."""

    class Meta:
        model = SellerProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    shop_name = factory.Sequence(lambda n: f"Test Shop {n}")
    slug = factory.Sequence(lambda n: f"test-shop-{n}-abcd1234")
    bio = "A great thrift shop."
    is_active = True
    is_verified_seller = False


class SellerSocialLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SellerSocialLink

    seller = factory.SubFactory(SellerProfileFactory)
    platform = SocialPlatform.INSTAGRAM
    url = "https://instagram.com/testshop"
