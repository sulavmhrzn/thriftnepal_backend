from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel
from apps.listings.enums import ListingCondition, ListingStatus


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    icon = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ListingManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset().filter(status=ListingStatus.ACTIVE, is_deleted=False)
        )


class AllListingManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class Listing(BaseModel):
    seller = models.ForeignKey(
        "profiles.SellerProfile", on_delete=models.CASCADE, related_name="listings"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="listings"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    condition = models.CharField(max_length=20, choices=ListingCondition.choices)
    status = models.CharField(
        max_length=20, choices=ListingStatus.choices, default=ListingStatus.DRAFT
    )

    is_negotiable = models.BooleanField(default=False)
    accepts_meetup = models.BooleanField(default=True)
    accepts_delivery = models.BooleanField(default=False)

    views_count = models.PositiveIntegerField(default=0)

    objects = ListingManager()
    all_objects = AllListingManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["seller"]),
            models.Index(fields=["category"]),
            models.Index(fields=["condition"]),
            models.Index(fields=["price"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.seller.shop_name}"


class ListingImage(BaseModel):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image_key = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        indexes = [
            models.Index(fields=["listing", "order"]),
        ]

    def __str__(self):
        return f"{self.listing.title} - image {self.order}"
