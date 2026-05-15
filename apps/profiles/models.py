from auditlog.registry import auditlog
from django.db import models

from apps.core.models import BaseModel
from apps.profiles.enums import District, Province, SocialPlatform


class SellerProfile(BaseModel):
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="seller_profile",
    )
    shop_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    bio = models.TextField(blank=True, null=True)

    province = models.CharField(
        max_length=50,
        choices=Province.choices,
        blank=True,
        null=True,
    )
    district = models.CharField(
        max_length=100,
        choices=District.choices,
        blank=True,
        null=True,
    )
    city = models.CharField(max_length=100, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)

    profile_picture = models.CharField(max_length=500, blank=True, null=True)
    banner_image = models.CharField(max_length=500, blank=True, null=True)

    is_verified_seller = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    government_id_key = models.CharField(max_length=500, blank=True, null=True)
    government_id_verified = models.BooleanField(default=False)

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    total_reviews = models.PositiveIntegerField(default=0)
    total_sales = models.PositiveIntegerField(default=0)
    total_listings = models.PositiveIntegerField(default=0)

    phone_number = models.CharField(max_length=20, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    accepts_meetup = models.BooleanField(default=True)
    accepts_delivery = models.BooleanField(default=False)

    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.shop_name} ({self.user.email})"


class SellerSocialLink(BaseModel):
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.CASCADE, related_name="social_links"
    )
    platform = models.CharField(max_length=50, choices=SocialPlatform.choices)
    url = models.URLField()

    class Meta:
        unique_together = ("seller", "platform")

    def __str__(self):
        return f"{self.seller.shop_name} - {self.platform}"


class BuyerProfile(BaseModel):
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="buyer_profile",
    )
    bio = models.TextField(blank=True, null=True)

    province = models.CharField(
        max_length=60,
        choices=Province.choices,
        blank=True,
        null=True,
    )
    district = models.CharField(
        max_length=100,
        choices=District.choices,
        blank=True,
        null=True,
    )
    city = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.CharField(max_length=500, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.full_name} ({self.user.email})"


class SavedListing(BaseModel):
    buyer = models.ForeignKey(
        BuyerProfile,
        on_delete=models.CASCADE,
        related_name="saved_listings",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="saved_by",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["buyer", "listing"], name="unique_buyer_saved_listing"
            )
        ]
        indexes = [
            models.Index(fields=["buyer"]),
            models.Index(fields=["listing"]),
        ]

    def __str__(self):
        return f"{self.buyer.user.full_name} -> {self.listing.title}"


auditlog.register(
    SellerProfile,
    exclude_fields=[
        "updated_at",
        "average_rating",
        "total_reviews",
        "total_sales",
        "total_listings",
    ],
)
auditlog.register(BuyerProfile, exclude_fields=["updated_at"])
auditlog.register(SellerSocialLink, exclude_fields=["updated_at"])
auditlog.register(SavedListing, exclude_fields=["updated_at"])
