from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import YAMLPermission
from apps.core.responses import success_response
from apps.profiles.selectors import (
    get_seller_profile_by_user,
    get_social_links_by_seller,
)
from apps.profiles.serializers import (
    BannerImageUploadSerializer,
    GovernmentIDUploadSerializer,
    ProfilePictureUploadSerializer,
    SellerProfileSerializer,
    SellerProfileUpdateSerializer,
    SellerSocialLinkSerializer,
    SellerSocialLinkUpdateSerializer,
)
from apps.profiles.services import (
    update_seller_profile,
    update_social_links,
    upload_banner_image,
    upload_government_id,
    upload_profile_picture,
)


class SellerProfileMeView(APIView):
    permission_classes = [IsAuthenticated, YAMLPermission]
    resource_name = "profiles"

    def get(self, request):
        seller = get_seller_profile_by_user(request.user)
        serializer = SellerProfileSerializer(seller)
        return success_response(
            message="Profile fetched successfully", data=serializer.data
        )

    def patch(self, request):
        seller = get_seller_profile_by_user(request.user)
        serializer = SellerProfileUpdateSerializer(
            instance=seller, data=request.data, context={"seller": seller}
        )
        serializer.is_valid(raise_exception=True)
        updated_profile = update_seller_profile(seller, serializer.validated_data)
        out = SellerProfileSerializer(updated_profile)
        return success_response(message="Profile updated successfully", data=out.data)


class SellerSocialLinksView(APIView):
    permission_classes = [IsAuthenticated, YAMLPermission]
    resource_name = "profiles"

    def get(self, request):
        seller = get_seller_profile_by_user(request.user)
        social_links = get_social_links_by_seller(seller)
        out = SellerSocialLinkSerializer(social_links, many=True)
        return success_response(
            message="Social links fetched successfully", data=out.data
        )

    def put(self, request):
        seller = get_seller_profile_by_user(request.user)
        serializer = SellerSocialLinkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_links = update_social_links(seller, serializer.validated_data["links"])
        out = SellerSocialLinkSerializer(updated_links, many=True)
        return success_response(
            message="Social links updated successfully", data=out.data
        )


class SellerProfilePictureView(APIView):
    permission_classes = [IsAuthenticated, YAMLPermission]
    resource_name = "profiles"

    def post(self, request):
        seller = get_seller_profile_by_user(request.user)

        serializer = ProfilePictureUploadSerializer(data=request.FILES)
        serializer.is_valid(raise_exception=True)
        updated_seller = upload_profile_picture(
            seller=seller,
            file=serializer.validated_data["file"],
        )
        return success_response(
            message="Profile picture uploaded successfully.",
            data=SellerProfileSerializer(updated_seller).data,
        )


class SellerBannerImageView(APIView):
    permission_classes = [IsAuthenticated, YAMLPermission]
    resource_name = "profiles"

    def post(self, request):
        seller = get_seller_profile_by_user(request.user)

        serializer = BannerImageUploadSerializer(data=request.FILES)
        serializer.is_valid(raise_exception=True)

        updated_seller = upload_banner_image(
            seller=seller,
            file=serializer.validated_data["file"],
        )

        return success_response(
            message="Banner image uploaded successfully.",
            data=SellerProfileSerializer(updated_seller).data,
        )


class SellerGovernmentIDView(APIView):
    permission_classes = [IsAuthenticated, YAMLPermission]
    resource_name = "profiles"

    def post(self, request):
        seller = get_seller_profile_by_user(request.user)

        serializer = GovernmentIDUploadSerializer(data=request.FILES)
        serializer.is_valid(raise_exception=True)

        upload_government_id(
            seller=seller,
            file=serializer.validated_data["file"],
        )

        return success_response(
            message="Government ID uploaded successfully. Pending admin review.",
        )
