from django.urls import path

from apps.profiles.views import (
    BuyerProfileMeView,
    BuyerProfilePictureView,
    SavedListingDetailView,
    SavedListingsView,
)

urlpatterns = [
    path("me/", BuyerProfileMeView.as_view(), name="buyer-profile"),
    path(
        "me/profile-picture/",
        BuyerProfilePictureView.as_view(),
        name="buyer-profile-picture",
    ),
    path("saved-listings/", SavedListingsView.as_view(), name="saved-listings"),
    path(
        "saved-listings/<uuid:saved_listing_id>/",
        SavedListingDetailView.as_view(),
        name="saved-listings-detail",
    ),
]
