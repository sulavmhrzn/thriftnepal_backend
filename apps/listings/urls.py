from django.urls import path

from apps.listings.views import (
    CategoryListView,
    ListingArchiveView,
    ListingDetailUpdateDeleteView,
    ListingImageDeleteView,
    ListingImageReorderView,
    ListingImageUploadView,
    ListingListCreateView,
    ListingMarkSoldView,
    ListingPublishView,
    ListingReactivateView,
    ListingSearchView,
    SellerListingListView,
)

urlpatterns = [
    # categories
    path("categories/", CategoryListView.as_view(), name="category-list"),
    # Seller dashboard
    path("me/", SellerListingListView.as_view(), name="seller-listings"),
    # Public listings
    path("", ListingListCreateView.as_view(), name="listing-list"),
    path("search/", ListingSearchView.as_view(), name="listing-search"),
    path(
        "<uuid:listing_id>/",
        ListingDetailUpdateDeleteView.as_view(),
        name="listing-detail",
    ),
    # Status transitions
    path(
        "<uuid:listing_id>/publish/",
        ListingPublishView.as_view(),
        name="listing-publish",
    ),
    path(
        "<uuid:listing_id>/sold/",
        ListingMarkSoldView.as_view(),
        name="listing-publish",
    ),
    path(
        "<uuid:listing_id>/archive/",
        ListingArchiveView.as_view(),
        name="listing-publish",
    ),
    path(
        "<uuid:listing_id>/reactivate/",
        ListingReactivateView.as_view(),
        name="listing-publish",
    ),
    # Images
    path(
        "<uuid:listing_id>/images/",
        ListingImageUploadView.as_view(),
        name="listing-image-upload",
    ),
    path(
        "<uuid:listing_id>/images/reorder/",
        ListingImageReorderView.as_view(),
        name="listing-image-reorder",
    ),
    path(
        "<uuid:listing_id>/images/<uuid:image_id>/",
        ListingImageDeleteView.as_view(),
        name="listing-image-delete",
    ),
]
