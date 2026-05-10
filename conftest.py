import factory
from django.contrib.auth import get_user_model

from apps.listings.enums import ListingCondition, ListingStatus
from apps.listings.models import Category, Listing, ListingImage
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


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")
    parent = None
    icon = None


class ListingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Listing
        exclude = ["_use_all_objects"]

    _use_all_objects = True

    seller = factory.SubFactory(SellerProfileFactory)
    category = factory.SubFactory(CategoryFactory)
    title = factory.Sequence(lambda n: f"Listing {n}")
    description = "A great item for sale."
    price = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    condition = ListingCondition.GOOD
    status = ListingStatus.DRAFT
    is_negotiable = False
    accepts_meetup = True
    accepts_delivery = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        kwargs.pop("_use_all_objects", None)
        return Listing.all_objects.create(*args, **kwargs)


class ListingImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ListingImage

    listing = factory.SubFactory(ListingFactory)
    image_key = factory.Sequence(lambda n: f"listings/listing-{n}/image.jpg")
    order = 0
