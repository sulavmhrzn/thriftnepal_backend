from django.urls import path

from apps.profiles.views import (
    ListTopSellerProfileView,
    SellerBannerImageView,
    SellerGovernmentIDView,
    SellerProfileDetailView,
    SellerProfileListView,
    SellerProfileMeView,
    SellerProfilePictureView,
    SellerSocialLinksView,
)

urlpatterns = [
    path("", SellerProfileListView.as_view(), name="seller-profile-list"),
    path("top-rated/", ListTopSellerProfileView.as_view(), name="seller-profile-top"),
    path("me/", SellerProfileMeView.as_view(), name="seller-profile-me"),
    path(
        "me/social-links/", SellerSocialLinksView.as_view(), name="seller-social-links"
    ),
    path(
        "me/profile-picture/",
        SellerProfilePictureView.as_view(),
        name="seller-profile-picture",
    ),
    path("me/banner/", SellerBannerImageView.as_view(), name="seller-banner-image"),
    path(
        "me/government-id/",
        SellerGovernmentIDView.as_view(),
        name="seller-government-id",
    ),
    path(
        "<slug:slug>/", SellerProfileDetailView.as_view(), name="seller-profile-detail"
    ),
]
