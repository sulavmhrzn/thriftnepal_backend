from django.urls import path

from apps.profiles.views import (
    SellerBannerImageView,
    SellerGovernmentIDView,
    SellerProfileMeView,
    SellerProfilePictureView,
    SellerSocialLinksView,
)

# GET     /api/sellers/{slug}/                  → SellerProfileDetailView
# GET     /api/sellers/me/                      → SellerProfileMeView [x]
# PATCH   /api/sellers/me/                      → SellerProfileMeView [x]
# POST    /api/sellers/me/profile-picture/      → SellerProfilePictureView
# POST    /api/sellers/me/banner/               → SellerBannerImageView
# POST    /api/sellers/me/government-id/        → SellerGovernmentIDView
# GET     /api/sellers/me/social-links/         → SellerSocialLinksView [x]
# PUT     /api/sellers/me/social-links/         → SellerSocialLinksView [x]
# GET     /api/sellers/top-rated/               → TopRatedSellersView

urlpatterns = [
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
]
