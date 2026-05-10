from rest_framework import serializers

from apps.core.minio import get_public_url
from apps.listings.enums import ListingCondition
from apps.listings.models import Category, Listing, ListingImage
from apps.listings.selectors import get_category_by_id


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon")


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "children"]


class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = ("id", "image_url", "order")

    def get_image_url(self, obj):
        if not obj.image_key:
            return None
        return get_public_url(obj.image_key)


class ListingSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    seller_shop_name = serializers.CharField(
        source="seller.shop_name",
        read_only=True,
    )
    seller_slug = serializers.CharField(
        source="seller.slug",
        read_only=True,
    )
    seller_is_verified = serializers.BooleanField(
        source="seller.is_verified_seller",
        read_only=True,
    )
    primary_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id",
            "title",
            "description",
            "price",
            "condition",
            "status",
            "is_negotiable",
            "accepts_meetup",
            "accepts_delivery",
            "views_count",
            "category",
            "seller_shop_name",
            "seller_slug",
            "seller_is_verified",
            "primary_image_url",
            "images",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_primary_image_url(self, obj):
        images = obj.images.all()
        if not images:
            return None
        return get_public_url(images[0].image_key)


class CreateListingSerializer(serializers.ModelSerializer):
    category_id = serializers.UUIDField()

    class Meta:
        model = Listing
        fields = (
            "title",
            "description",
            "price",
            "condition",
            "is_negotiable",
            "accepts_meetup",
            "accepts_delivery",
            "category_id",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate_condition(self, value):
        if value not in ListingCondition.values:
            raise serializers.ValidationError("Invalid condition.")
        return value

    def validate_category_id(self, value):
        get_category_by_id(value)
        return value


class UpdateListingSerializer(CreateListingSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class ListingImageUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()

    def validate_file(self, file):
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        max_size = 5 * 1024 * 1024
        if file.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: jpeg, png, webp."
            )

        if file.size > max_size:
            raise serializers.ValidationError("Image too large. Maximum size is 5MB.")

        return file


class ListingImageReorderSerializer(serializers.Serializer):
    image_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        min_length=1,
        max_length=8,
    )
