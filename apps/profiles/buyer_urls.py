from django.urls import path

from apps.profiles.views import BuyerProfileMeView, BuyerProfilePictureView

urlpatterns = [
    path("me/", BuyerProfileMeView.as_view(), name="buyer-profile"),
    path(
        "me/profile-picture/",
        BuyerProfilePictureView.as_view(),
        name="buyer-profile-picture",
    ),
]
