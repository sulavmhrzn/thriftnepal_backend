import structlog
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.pagination import DefaultCursorPagination
from apps.core.permissions import YAMLPermission
from apps.core.responses import get_paginated_data, paginated_response, success_response
from apps.listings.enums import ListingStatus
from apps.listings.search import search_listings
from apps.listings.selectors import (
    get_active_listings,
    get_all_categories,
    get_listing_by_id,
    get_listing_by_id_for_seller,
    get_listing_image_by_id,
    get_listings_by_seller,
)
from apps.listings.serializers import (
    CategoryDetailSerializer,
    CreateListingSerializer,
    ListingImageReorderSerializer,
    ListingImageSerializer,
    ListingImageUploadSerializer,
    ListingSerializer,
    UpdateListingSerializer,
)
from apps.listings.services import (
    archive_listing,
    create_listing,
    delete_listing_image,
    increment_views_count,
    mark_listing_as_sold,
    publish_listing,
    reactivate_listing,
    reorder_listing_images,
    soft_delete_listing,
    update_listing,
    upload_listing_image,
)
from apps.profiles.selectors import get_seller_profile_by_user

logger = structlog.get_logger(__name__)


def _parse_bool(value):
    if value is None:
        return None
    return value.lower() == "true"


class SellerListingMixin:
    resource_name = "listings"
    permission_classes = [IsAuthenticated, YAMLPermission]

    def get_seller_listing(self, request, listing_id):
        seller = get_seller_profile_by_user(request.user)
        return get_listing_by_id_for_seller(listing_id, seller)


class CategoryListView(APIView):
    def get(self, request):
        categories = get_all_categories()
        return success_response(
            message="Categories fetched successfully",
            data=CategoryDetailSerializer(categories, many=True).data,
        )


class ListingListCreateView(APIView):
    resource_name = "listings"

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), YAMLPermission()]

    def get(self, request):
        filters = {
            "category_slug": request.query_params.get("category_slug"),
            "condition": request.query_params.get("condition"),
            "min_price": request.query_params.get("min_price"),
            "max_price": request.query_params.get("max_price"),
            "is_negotiable": _parse_bool(request.query_params.get("is_negotiable")),
            "accepts_meetup": _parse_bool(request.query_params.get("accepts_meetup")),
            "accepts_delivery": _parse_bool(
                request.query_params.get("accepts_delivery")
            ),
        }
        filters = {k: v for k, v in filters.items() if v is not None}

        listings = get_active_listings(filters)
        result = get_paginated_data(
            DefaultCursorPagination(),
            queryset=listings,
            request=request,
            serializer_class=ListingSerializer,
        )
        result["message"] = "Listings fetched successfully"
        return paginated_response(**result)

    def post(self, request):
        seller = get_seller_profile_by_user(request.user)

        serializer = CreateListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing = create_listing(seller=seller, data=serializer.validated_data)
        return success_response(
            message="Listing created successfully. Add images then publish.",
            data=ListingSerializer(listing).data,
            status_code=status.HTTP_201_CREATED,
        )


class ListingDetailUpdateDeleteView(APIView):
    resource_name = "listings"

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), YAMLPermission()]

    def get(self, request, listing_id):
        listing = get_listing_by_id(listing_id=listing_id)

        try:
            increment_views_count()
        except Exception:
            pass

        serializer = ListingSerializer(listing)
        return success_response(
            message="Listing fetched successfully",
            data=serializer.data,
        )

    def patch(self, request, listing_id):
        seller = get_seller_profile_by_user(request.user)
        listing = get_listing_by_id_for_seller(listing_id, seller)

        serializer = UpdateListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_listing = update_listing(listing, serializer.validated_data)
        return success_response(
            message="Listing updated successfully",
            data=ListingSerializer(updated_listing).data,
        )

    def delete(self, request, listing_id):
        seller = get_seller_profile_by_user(request.user)
        listing = get_listing_by_id_for_seller(listing_id, seller)

        soft_delete_listing(listing=listing, request=request)

        return success_response(
            message="Listing deleted successfully.",
        )


class ListingPublishView(SellerListingMixin, APIView):
    def post(self, request, listing_id):
        listing = self.get_seller_listing(request, listing_id)

        updated_listing = publish_listing(listing)

        return success_response(
            message="Listing published successfully.",
            data=ListingSerializer(updated_listing).data,
        )


class ListingMarkSoldView(SellerListingMixin, APIView):
    def post(self, request, listing_id):
        listing = self.get_seller_listing(request, listing_id)
        updated_listing = mark_listing_as_sold(listing, request)

        return success_response(
            message="Listing marked as sold",
            data=ListingSerializer(updated_listing).data,
        )


class ListingArchiveView(SellerListingMixin, APIView):
    def post(self, request, listing_id):
        listing = self.get_seller_listing(request, listing_id)
        updated_listing = archive_listing(listing)

        return success_response(
            message="Listing archived successfully",
            data=ListingSerializer(updated_listing).data,
        )


class ListingReactivateView(SellerListingMixin, APIView):
    def post(self, request, listing_id):
        listing = self.get_seller_listing(request, listing_id)
        updated_listing = reactivate_listing(listing)

        return success_response(
            message="Listing reactivated successfully",
            data=ListingSerializer(updated_listing).data,
        )


class ListingImageUploadView(SellerListingMixin, APIView):
    def post(self, request, listing_id):
        listing = self.get_seller_listing(request, listing_id)

        serializer = ListingImageUploadSerializer(data=request.FILES)
        serializer.is_valid(raise_exception=True)

        image = upload_listing_image(
            listing=listing,
            file=serializer.validated_data["file"],
        )

        return success_response(
            message="Image uploaded successfully.",
            data=ListingImageSerializer(image).data,
            status_code=status.HTTP_201_CREATED,
        )


class ListingImageReorderView(SellerListingMixin, APIView):
    def put(self, request, listing_id):
        listing = self.get_seller_listing(request, listing_id)

        serializer = ListingImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        images = reorder_listing_images(
            listing=listing,
            image_ids=serializer.validated_data["image_ids"],
        )
        return success_response(
            message="Image reordered successfully",
            data=ListingImageSerializer(images, many=True).data,
        )


class ListingImageDeleteView(SellerListingMixin, APIView):
    def delete(self, request, listing_id, image_id):
        listing = self.get_seller_listing(request, listing_id)
        image = get_listing_image_by_id(image_id, listing)
        delete_listing_image(image)
        return success_response(message="Image deleted successfully")


class SellerListingListView(APIView):
    permission_classes = [IsAuthenticated, YAMLPermission]
    resource_name = "listings"

    def get(self, request):
        seller = get_seller_profile_by_user(request.user)
        filters = {"status": request.query_params.get("status")}
        filters = {k: v for k, v in filters.items() if v is not None}

        if status_filter := filters.get("status"):
            if status_filter not in ListingStatus.values:
                raise ValidationError(
                    {
                        "status": [
                            f"Invalid status. Choices are: {', '.join(ListingStatus.values)}"
                        ]
                    }
                )

        listings = get_listings_by_seller(seller=seller, filters=filters)
        result = get_paginated_data(
            paginator=DefaultCursorPagination(),
            queryset=listings,
            request=request,
            serializer_class=ListingSerializer,
        )
        result["message"] = "Your listings fetched successfully"
        return paginated_response(**result)


class ListingSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        try:
            page = int(request.query_params.get("page", 1))
            if page < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError({"page": ["Must be a positive integer."]})

        try:
            page_size = int(request.query_params.get("page_size", 20))
            if page_size < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError({"page_size": ["Must be a positive integer."]})

        filters = {
            "condition": request.query_params.get("condition"),
            "category_slug": request.query_params.get("category_slug"),
            "min_price": request.query_params.get("min_price"),
            "max_price": request.query_params.get("max_price"),
            "is_negotiable": _parse_bool(request.query_params.get("is_negotiable")),
            "accepts_meetup": _parse_bool(request.query_params.get("accepts_meetup")),
            "accepts_delivery": _parse_bool(
                request.query_params.get("accepts_delivery")
            ),
            "seller_province": request.query_params.get("province"),
            "is_verified_seller": _parse_bool(
                request.query_params.get("verified_seller")
            ),
        }

        filters = {k: v for k, v in filters.items() if v is not None}

        result = search_listings(
            query=query or None,
            filters=filters,
            page=page,
            page_size=page_size,
        )

        return paginated_response(
            message="Search results fetched successfully",
            data=ListingSerializer(result["listings"], many=True).data,
            pagination={
                "total": result["total"],
                "page": result["page"],
                "pages": result["pages"],
                "page_size": result["page_size"],
                "facets": result["facets"],
            },
        )
