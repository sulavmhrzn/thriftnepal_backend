from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/sellers/", include("apps.profiles.seller_urls")),
    path("api/v1/buyers/", include("apps.profiles.buyer_urls")),
    path("api/v1/listings/", include("apps.listings.urls")),
]
