import os

from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.core.minio import generate_presigned_url, get_public_url
from apps.listings.enums import ListingStatus
from apps.listings.serializers import ListingSerializer
from apps.profiles.enums import SocialPlatform
from apps.profiles.models import BuyerProfile, SavedListing, SellerProfile

ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
ALLOWED_DOCUMENT_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


class SellerProfileUpdateSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    shop_name = serializers.CharField(
        validators=[
            UniqueValidator(
                queryset=SellerProfile.objects.all(),
                message="Shop with this name already exists.",
                lookup="iexact",
            )
        ]
    )
    phone_number = PhoneNumberField(required=False)

    class Meta:
        model = SellerProfile
        fields = [
            "shop_name",
            "bio",
            "province",
            "district",
            "city",
            "landmark",
            "phone_number",
            "accepts_meetup",
            "accepts_delivery",
            "meta_title",
            "meta_description",
        ]


class SellerSocialLinkSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=SocialPlatform.choices)
    url = serializers.URLField()


class SellerProfilePublicSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    banner_image_url = serializers.SerializerMethodField()
    social_links = SellerSocialLinkSerializer(many=True)

    class Meta:
        model = SellerProfile
        fields = [
            "id",
            "email",
            "shop_name",
            "slug",
            "bio",
            "province",
            "district",
            "city",
            "landmark",
            "phone_number",
            "is_verified_seller",
            "is_active",
            "accepts_meetup",
            "accepts_delivery",
            "average_rating",
            "total_reviews",
            "total_sales",
            "total_listings",
            "meta_title",
            "meta_description",
            "social_links",
            "created_at",
            "updated_at",
            "profile_picture_url",
            "banner_image_url",
        ]
        read_only_fields = fields

    def get_profile_picture_url(self, obj):
        if not obj.profile_picture:
            return None
        return get_public_url(obj.profile_picture)

    def get_banner_image_url(self, obj):
        if not obj.banner_image:
            return None
        return get_public_url(obj.banner_image)


class SellerProfilePrivateSerializer(SellerProfilePublicSerializer):
    """
    Output serializer. Read only.
    Generates presigned MinIO URLs from stored object keys.
    """

    government_id_url = serializers.SerializerMethodField()

    class Meta(SellerProfilePublicSerializer.Meta):
        fields = SellerProfilePublicSerializer.Meta.fields + [
            "government_id_url",
            "government_id_verified",
        ]
        read_only_fields = fields

    def get_government_id_url(self, obj):
        if not obj.government_id_key:
            return None
        return generate_presigned_url(obj.government_id_key)


class SellerSocialLinkUpdateSerializer(serializers.Serializer):
    links = SellerSocialLinkSerializer(many=True, allow_empty=True)

    def validate_links(self, links):
        platforms = [link["platform"] for link in links]

        if len(platforms) != len(set(platforms)):
            raise serializers.ValidationError("Duplicate platforms not allowed.")

        return links


class ProfilePictureUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()

    def validate_file(self, file):
        if file.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("File too large. Maximum size is 5MB.")

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported extension. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        return file


class BannerImageUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()

    def validate_file(self, file):
        if file.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("File too large. Maximum size is 5MB.")

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported extension. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        return file


class GovernmentIDUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):
        if file.size > MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError("File too large. Maximum size is 10MB.")

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported extension. Allowed: {', '.join(ALLOWED_DOCUMENT_EXTENSIONS)}"
            )

        return file


class BuyerProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = BuyerProfile
        fields = [
            "id",
            "full_name",
            "email",
            "bio",
            "province",
            "district",
            "city",
            "phone_number",
            "avatar_url",
            "created_at",
            "updated_at",
        ]

    def get_avatar_url(self, obj) -> str | None:
        if obj.profile_picture:
            return get_public_url(obj.profile_picture)
        return None


class BuyerProfileUpdateSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    class Meta:
        model = BuyerProfile
        fields = [
            "bio",
            "province",
            "district",
            "city",
            "phone_number",
        ]


class SavedListingSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = SavedListing
        fields = (
            "id",
            "listing",
            "is_available",
            "created_at",
        )
        read_only_fields = fields

    def get_is_available(self, obj) -> bool:
        return obj.listing.status == ListingStatus.ACTIVE
