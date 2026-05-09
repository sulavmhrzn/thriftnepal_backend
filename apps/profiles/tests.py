"""
Comprehensive tests for the profiles app.

Covers:
  - Models (str, constraints)
  - Signals (auto-create SellerProfile on seller user creation)
  - Selectors (happy path + not-found)
  - Services (update profile, social links, file upload validation)
  - Serializers (field validation, duplicate-platform check, file size/ext)
  - Views (authentication, role-based access, CRUD via API client)
"""

import io
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.test import APIClient

from apps.profiles.enums import Province, SocialPlatform
from apps.profiles.models import SellerProfile, SellerSocialLink
from apps.profiles.selectors import (
    get_all_active_sellers,
    get_seller_profile_by_slug,
    get_seller_profile_by_user,
    get_social_links_by_seller,
    get_top_rated_sellers,
)
from apps.profiles.serializers import (
    GovernmentIDUploadSerializer,
    ProfilePictureUploadSerializer,
    SellerProfileUpdateSerializer,
    SellerSocialLinkUpdateSerializer,
)
from apps.profiles.services import (
    _validate_file,
    update_seller_profile,
    update_social_links,
)
from apps.users.enums import UserRole

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.django_db


def _make_fake_file(name="photo.jpg", content_type="image/jpeg", size_bytes=1024):
    """Return a minimal in-memory file-like object suitable for service/serializer tests."""
    data = b"x" * size_bytes
    file = io.BytesIO(data)
    file.name = name
    file.content_type = content_type
    file.size = size_bytes
    return file


def _make_real_image_upload(name="photo.jpg", content_type="image/jpeg", fmt="JPEG"):
    """Return a SimpleUploadedFile containing real image bytes (Pillow-validated)."""
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


# ---------------------------------------------------------------------------
# Fixtures (imported from conftest via factory-boy)
# ---------------------------------------------------------------------------


@pytest.fixture()
def buyer(db):
    from conftest import UserFactory

    return UserFactory(role=UserRole.BUYER)


@pytest.fixture()
def seller_user(db):
    """A User with SELLER role — signal creates SellerProfile automatically."""
    from conftest import SellerUserFactory

    return SellerUserFactory()


@pytest.fixture()
def seller_profile(seller_user):
    """The SellerProfile created by the signal for seller_user."""
    return SellerProfile.objects.get(user=seller_user)


@pytest.fixture()
def another_seller_profile(db):
    from conftest import SellerProfileFactory

    return SellerProfileFactory(
        shop_name="Another Shop",
        slug="another-shop-xxxx1234",
        is_active=True,
        is_verified_seller=True,
        average_rating=Decimal("4.50"),
    )


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def auth_client(seller_user, api_client):
    api_client.force_authenticate(user=seller_user)
    return api_client


@pytest.fixture()
def buyer_client(buyer, api_client):
    new_client = APIClient()
    new_client.force_authenticate(user=buyer)
    return new_client


# ===========================================================================
# 1. MODEL TESTS
# ===========================================================================


class TestSellerProfileModel:
    def test_str_representation(self, seller_profile, seller_user):
        expected = f"{seller_profile.shop_name} ({seller_user.email})"
        assert str(seller_profile) == expected

    def test_default_values(self, seller_profile):
        assert seller_profile.is_active is True
        assert seller_profile.is_verified_seller is False
        assert seller_profile.accepts_meetup is True
        assert seller_profile.accepts_delivery is False
        assert seller_profile.average_rating == Decimal("0.00")
        assert seller_profile.total_reviews == 0
        assert seller_profile.total_sales == 0
        assert seller_profile.total_listings == 0

    def test_shop_name_unique(self, seller_profile, db):
        from conftest import UserFactory

        other_user = UserFactory()
        with pytest.raises(Exception):
            SellerProfile.objects.create(
                user=other_user,
                shop_name=seller_profile.shop_name,
                slug="different-slug-zzzz9999",
            )

    def test_slug_unique(self, seller_profile, db):
        from conftest import UserFactory

        other_user = UserFactory()
        with pytest.raises(Exception):
            SellerProfile.objects.create(
                user=other_user,
                shop_name="Totally Different Name",
                slug=seller_profile.slug,
            )


class TestSellerSocialLinkModel:
    def test_str_representation(self, seller_profile):
        link = SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.INSTAGRAM,
            url="https://instagram.com/shop",
        )
        expected = f"{seller_profile.shop_name} - {SocialPlatform.INSTAGRAM}"
        assert str(link) == expected

    def test_unique_together_platform_per_seller(self, seller_profile):
        SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.FACEBOOK,
            url="https://facebook.com/shop",
        )
        with pytest.raises(Exception):
            SellerSocialLink.objects.create(
                seller=seller_profile,
                platform=SocialPlatform.FACEBOOK,
                url="https://facebook.com/shop2",
            )


# ===========================================================================
# 2. SIGNAL TESTS
# ===========================================================================


class TestSellerProfileSignal:
    def test_seller_profile_auto_created_for_seller(self, seller_user):
        assert SellerProfile.objects.filter(user=seller_user).exists()

    def test_seller_profile_not_created_for_buyer(self, buyer):
        assert not SellerProfile.objects.filter(user=buyer).exists()

    def test_seller_profile_not_duplicated_on_save(self, seller_user):
        seller_user.full_name = "Updated Name"
        seller_user.save()
        assert SellerProfile.objects.filter(user=seller_user).count() == 1

    def test_slug_is_set_on_auto_created_profile(self, seller_user):
        profile = SellerProfile.objects.get(user=seller_user)
        assert profile.slug
        assert len(profile.slug) > 0


# ===========================================================================
# 3. SELECTOR TESTS
# ===========================================================================


class TestGetSellerProfileByUser:
    def test_returns_profile_for_valid_user(self, seller_user, seller_profile):
        result = get_seller_profile_by_user(seller_user)
        assert result == seller_profile

    def test_raises_not_found_for_buyer(self, buyer):
        with pytest.raises(NotFound):
            get_seller_profile_by_user(buyer)


class TestGetSellerProfileBySlug:
    def test_returns_profile_for_valid_slug(self, seller_profile):
        result = get_seller_profile_by_slug(seller_profile.slug)
        assert result == seller_profile

    def test_raises_not_found_for_invalid_slug(self):
        with pytest.raises(NotFound):
            get_seller_profile_by_slug("nonexistent-slug-xxxx0000")


class TestGetTopRatedSellers:
    def test_returns_only_verified_and_active(
        self, seller_profile, another_seller_profile
    ):
        # seller_profile is not verified → excluded
        results = get_top_rated_sellers()
        ids = [s.id for s in results]
        assert another_seller_profile.id in ids
        assert seller_profile.id not in ids

    def test_respects_limit(self, db):
        from conftest import SellerProfileFactory

        for i in range(5):
            SellerProfileFactory(
                shop_name=f"TopShop{i}",
                slug=f"topshop{i}-abcd1234",
                is_active=True,
                is_verified_seller=True,
                average_rating=Decimal("4.00"),
            )
        results = get_top_rated_sellers(limit=3)
        assert len(results) <= 3

    def test_ordered_by_average_rating_desc(self, db):
        from conftest import SellerProfileFactory

        low = SellerProfileFactory(
            shop_name="Low Rated",
            slug="low-rated-aaaa0001",
            is_active=True,
            is_verified_seller=True,
            average_rating=Decimal("2.00"),
        )
        high = SellerProfileFactory(
            shop_name="High Rated",
            slug="high-rated-aaaa0002",
            is_active=True,
            is_verified_seller=True,
            average_rating=Decimal("4.99"),
        )
        results = list(get_top_rated_sellers(limit=10))
        high_idx = next(i for i, s in enumerate(results) if s.id == high.id)
        low_idx = next(i for i, s in enumerate(results) if s.id == low.id)
        assert high_idx < low_idx


class TestGetAllActiveSellers:
    def test_excludes_inactive_sellers(self, seller_profile, db):
        from conftest import SellerProfileFactory

        inactive = SellerProfileFactory(
            shop_name="Inactive Shop",
            slug="inactive-shop-zzzz9999",
            is_active=False,
        )
        results = get_all_active_sellers()
        ids = [s.id for s in results]
        assert inactive.id not in ids

    def test_includes_active_sellers(self, seller_profile):
        results = get_all_active_sellers()
        ids = [s.id for s in results]
        assert seller_profile.id in ids


class TestGetSocialLinksBySeller:
    def test_returns_links_for_seller(self, seller_profile):
        link = SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.TIKTOK,
            url="https://tiktok.com/@shop",
        )
        results = get_social_links_by_seller(seller_profile)
        assert link in results

    def test_returns_empty_when_no_links(self, seller_profile):
        results = get_social_links_by_seller(seller_profile)
        assert list(results) == []

    def test_ordered_by_platform(self, seller_profile):
        SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.YOUTUBE,
            url="https://youtube.com/shop",
        )
        SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.FACEBOOK,
            url="https://facebook.com/shop",
        )
        results = list(get_social_links_by_seller(seller_profile))
        platforms = [r.platform for r in results]
        assert platforms == sorted(platforms)


# ===========================================================================
# 4. SERVICE TESTS
# ===========================================================================


class TestUpdateSellerProfile:
    def test_updates_basic_fields(self, seller_profile):
        data = {"bio": "Updated bio", "city": "Kathmandu"}
        updated = update_seller_profile(seller_profile, data)
        assert updated.bio == "Updated bio"
        assert updated.city == "Kathmandu"

    def test_shop_name_change_regenerates_slug(self, seller_profile):
        old_slug = seller_profile.slug
        data = {"shop_name": "Brand New Shop Name"}
        with patch("apps.profiles.services.generate_unique_slug") as mock_slug:
            mock_slug.return_value = "brand-new-shop-name-abcd1234"
            updated = update_seller_profile(seller_profile, data)
        assert updated.slug != old_slug
        assert updated.shop_name == "Brand New Shop Name"

    def test_same_shop_name_does_not_change_slug(self, seller_profile):
        old_slug = seller_profile.slug
        data = {"shop_name": seller_profile.shop_name}
        updated = update_seller_profile(seller_profile, data)
        assert updated.slug == old_slug

    def test_persists_changes_to_db(self, seller_profile):
        update_seller_profile(seller_profile, {"bio": "Persisted bio"})
        refreshed = SellerProfile.objects.get(pk=seller_profile.pk)
        assert refreshed.bio == "Persisted bio"


class TestUpdateSocialLinks:
    def test_replaces_existing_links(self, seller_profile):
        SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.FACEBOOK,
            url="https://facebook.com/old",
        )
        new_data = [
            {"platform": SocialPlatform.INSTAGRAM, "url": "https://instagram.com/new"}
        ]
        result = update_social_links(seller_profile, new_data)
        assert len(result) == 1
        assert result[0].platform == SocialPlatform.INSTAGRAM

    def test_clears_links_when_empty_list(self, seller_profile):
        SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.TIKTOK,
            url="https://tiktok.com/@shop",
        )
        result = update_social_links(seller_profile, [])
        assert result == []
        assert not SellerSocialLink.objects.filter(seller=seller_profile).exists()

    def test_creates_multiple_links(self, seller_profile):
        data = [
            {"platform": SocialPlatform.FACEBOOK, "url": "https://facebook.com/shop"},
            {"platform": SocialPlatform.YOUTUBE, "url": "https://youtube.com/shop"},
        ]
        result = update_social_links(seller_profile, data)
        assert len(result) == 2


class TestValidateFile:
    def test_passes_for_valid_image(self):
        file = _make_fake_file("photo.jpg", "image/jpeg", 1024)
        _validate_file(
            file, {"image/jpeg", "image/png"}, 5 * 1024 * 1024
        )  # no exception

    def test_raises_for_invalid_content_type(self):
        file = _make_fake_file("doc.txt", "text/plain", 1024)
        with pytest.raises(ValidationError) as exc_info:
            _validate_file(file, {"image/jpeg"}, 5 * 1024 * 1024)
        assert "Unsupported file type" in str(exc_info.value)

    def test_raises_when_file_too_large(self):
        big = 6 * 1024 * 1024
        file = _make_fake_file("big.jpg", "image/jpeg", big)
        with pytest.raises(ValidationError) as exc_info:
            _validate_file(file, {"image/jpeg"}, 5 * 1024 * 1024)
        assert "too large" in str(exc_info.value)


class TestUploadProfilePicture:
    @patch(
        "apps.profiles.services.upload_file",
        return_value="seller-profiles/abc/profile/img.jpg",
    )
    @patch("apps.profiles.services.delete_file")
    def test_uploads_and_saves_key(self, mock_delete, mock_upload, seller_profile):
        from apps.profiles.services import upload_profile_picture

        file = _make_fake_file("photo.jpg", "image/jpeg", 1024)
        result = upload_profile_picture(seller_profile, file)
        assert result.profile_picture == "seller-profiles/abc/profile/img.jpg"
        mock_upload.assert_called_once()

    @patch("apps.profiles.services.upload_file", return_value="new-key.jpg")
    @patch("apps.profiles.services.delete_file")
    def test_deletes_old_picture_before_upload(
        self, mock_delete, mock_upload, seller_profile
    ):
        from apps.profiles.services import upload_profile_picture

        seller_profile.profile_picture = "old-key.jpg"
        seller_profile.save()
        file = _make_fake_file("photo.jpg", "image/jpeg", 1024)
        upload_profile_picture(seller_profile, file)
        mock_delete.assert_called_once_with("old-key.jpg", private=False)

    def test_raises_for_invalid_file_type(self, seller_profile):
        from apps.profiles.services import upload_profile_picture

        file = _make_fake_file("doc.pdf", "application/pdf", 1024)
        with pytest.raises(ValidationError):
            upload_profile_picture(seller_profile, file)


class TestUploadBannerImage:
    @patch(
        "apps.profiles.services.upload_file",
        return_value="seller-profiles/abc/banner/img.jpg",
    )
    @patch("apps.profiles.services.delete_file")
    def test_uploads_and_saves_key(self, mock_delete, mock_upload, seller_profile):
        from apps.profiles.services import upload_banner_image

        file = _make_fake_file("banner.jpg", "image/jpeg", 1024)
        result = upload_banner_image(seller_profile, file)
        assert result.banner_image == "seller-profiles/abc/banner/img.jpg"

    @patch("apps.profiles.services.upload_file", return_value="new-banner.jpg")
    @patch("apps.profiles.services.delete_file")
    def test_deletes_old_banner_before_upload(
        self, mock_delete, mock_upload, seller_profile
    ):
        from apps.profiles.services import upload_banner_image

        seller_profile.banner_image = "old-banner.jpg"
        seller_profile.save()
        file = _make_fake_file("banner.jpg", "image/jpeg", 1024)
        upload_banner_image(seller_profile, file)
        mock_delete.assert_called_once_with("old-banner.jpg", private=False)


class TestUploadGovernmentID:
    @patch(
        "apps.profiles.services.upload_file",
        return_value="seller-profiles/abc/government-id/id.pdf",
    )
    @patch("apps.profiles.services.delete_file")
    def test_uploads_and_resets_verified_flag(
        self, mock_delete, mock_upload, seller_profile
    ):
        from apps.profiles.services import upload_government_id

        seller_profile.government_id_verified = True
        seller_profile.save()
        file = _make_fake_file("id.pdf", "application/pdf", 2048)
        result = upload_government_id(seller_profile, file)
        assert result.government_id_key == "seller-profiles/abc/government-id/id.pdf"
        assert result.government_id_verified is False

    def test_raises_for_oversized_document(self, seller_profile):
        from apps.profiles.services import upload_government_id

        file = _make_fake_file("id.pdf", "application/pdf", 11 * 1024 * 1024)
        with pytest.raises(ValidationError):
            upload_government_id(seller_profile, file)


# ===========================================================================
# 5. SERIALIZER TESTS
# ===========================================================================


class TestSellerProfileUpdateSerializer:
    def test_valid_data_passes(self, seller_profile):
        data = {"bio": "Hello", "city": "Pokhara", "province": Province.GANDAKI}
        s = SellerProfileUpdateSerializer(
            instance=seller_profile, data=data, context={"seller": seller_profile}
        )
        assert s.is_valid(), s.errors

    def test_duplicate_shop_name_fails(self, seller_profile, another_seller_profile):
        data = {"shop_name": another_seller_profile.shop_name}
        s = SellerProfileUpdateSerializer(
            instance=seller_profile, data=data, context={"seller": seller_profile}
        )
        assert not s.is_valid()
        assert "shop_name" in s.errors

    def test_all_fields_optional(self, seller_profile):
        s = SellerProfileUpdateSerializer(
            instance=seller_profile, data={}, context={"seller": seller_profile}
        )
        assert s.is_valid(), s.errors


class TestSellerSocialLinkUpdateSerializer:
    def test_valid_links_pass(self):
        data = {
            "links": [
                {"platform": "instagram", "url": "https://instagram.com/shop"},
                {"platform": "facebook", "url": "https://facebook.com/shop"},
            ]
        }
        s = SellerSocialLinkUpdateSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_duplicate_platforms_fail(self):
        data = {
            "links": [
                {"platform": "instagram", "url": "https://instagram.com/shop"},
                {"platform": "instagram", "url": "https://instagram.com/shop2"},
            ]
        }
        s = SellerSocialLinkUpdateSerializer(data=data)
        assert not s.is_valid()
        assert "links" in s.errors

    def test_empty_links_allowed(self):
        s = SellerSocialLinkUpdateSerializer(data={"links": []})
        assert s.is_valid(), s.errors

    def test_invalid_platform_fails(self):
        data = {"links": [{"platform": "myspace", "url": "https://myspace.com/shop"}]}
        s = SellerSocialLinkUpdateSerializer(data=data)
        assert not s.is_valid()


class TestProfilePictureUploadSerializer:
    def test_valid_image_passes(self):
        img = _make_real_image_upload()
        s = ProfilePictureUploadSerializer(data={"file": img})
        assert s.is_valid(), s.errors

    def test_oversized_file_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        big_data = b"x" * (6 * 1024 * 1024)
        img = SimpleUploadedFile("photo.jpg", big_data, content_type="image/jpeg")
        s = ProfilePictureUploadSerializer(data={"file": img})
        assert not s.is_valid()
        assert "file" in s.errors

    def test_disallowed_extension_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        gif = SimpleUploadedFile("anim.gif", b"GIF89a", content_type="image/gif")
        s = ProfilePictureUploadSerializer(data={"file": gif})
        assert not s.is_valid()
        assert "file" in s.errors


class TestGovernmentIDUploadSerializer:
    def test_valid_pdf_passes(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        doc = SimpleUploadedFile("id.pdf", b"%PDF-data", content_type="application/pdf")
        s = GovernmentIDUploadSerializer(data={"file": doc})
        assert s.is_valid(), s.errors

    def test_oversized_document_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        big_data = b"x" * (11 * 1024 * 1024)
        doc = SimpleUploadedFile("id.pdf", big_data, content_type="application/pdf")
        s = GovernmentIDUploadSerializer(data={"file": doc})
        assert not s.is_valid()
        assert "file" in s.errors

    def test_disallowed_extension_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        exe = SimpleUploadedFile(
            "virus.exe", b"MZ", content_type="application/octet-stream"
        )
        s = GovernmentIDUploadSerializer(data={"file": exe})
        assert not s.is_valid()
        assert "file" in s.errors


# ===========================================================================
# 6. VIEW TESTS
# ===========================================================================


class TestSellerProfileMeView:
    url = reverse("seller-profile-me")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_buyer_has_no_seller_profile(self, buyer_client):
        # Buyers have "retrieve" permission but no SellerProfile → 404
        response = buyer_client.get(self.url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_seller_can_get_own_profile(self, auth_client, seller_profile):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["shop_name"] == seller_profile.shop_name

    def test_seller_can_patch_profile(self, auth_client, seller_profile):
        response = auth_client.patch(
            self.url, data={"bio": "Updated bio"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["bio"] == "Updated bio"

    def test_patch_with_duplicate_shop_name_returns_400(
        self, auth_client, seller_profile, another_seller_profile
    ):
        response = auth_client.patch(
            self.url,
            data={"shop_name": another_seller_profile.shop_name},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSellerSocialLinksView:
    url = reverse("seller-social-links")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_seller_can_get_social_links(self, auth_client, seller_profile):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_seller_can_update_social_links(self, auth_client, seller_profile):
        payload = {
            "links": [{"platform": "instagram", "url": "https://instagram.com/shop"}]
        }
        response = auth_client.put(self.url, data=payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["platform"] == "instagram"

    def test_seller_can_clear_social_links(self, auth_client, seller_profile):
        SellerSocialLink.objects.create(
            seller=seller_profile,
            platform=SocialPlatform.TIKTOK,
            url="https://tiktok.com/@shop",
        )
        response = auth_client.put(self.url, data={"links": []}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"] == []

    def test_duplicate_platforms_returns_400(self, auth_client, seller_profile):
        payload = {
            "links": [
                {"platform": "instagram", "url": "https://instagram.com/a"},
                {"platform": "instagram", "url": "https://instagram.com/b"},
            ]
        }
        response = auth_client.put(self.url, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSellerProfileDetailView:
    def test_public_can_view_seller_by_slug(self, api_client, seller_profile):
        url = reverse("seller-profile-detail", kwargs={"slug": seller_profile.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["slug"] == seller_profile.slug

    def test_invalid_slug_returns_404(self, api_client):
        url = reverse("seller-profile-detail", kwargs={"slug": "no-such-shop-xxxx0000"})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSellerProfileListView:
    url = reverse("seller-profile-list")

    def test_public_can_list_sellers(self, api_client, seller_profile):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        slugs = [s["slug"] for s in response.data["data"]]
        assert seller_profile.slug in slugs

    def test_inactive_sellers_excluded(self, api_client, db):
        from conftest import SellerProfileFactory

        inactive = SellerProfileFactory(
            shop_name="Gone Shop",
            slug="gone-shop-xxxx0001",
            is_active=False,
        )
        response = api_client.get(self.url)
        slugs = [s["slug"] for s in response.data["data"]]
        assert inactive.slug not in slugs


class TestListTopSellerProfileView:
    url = reverse("seller-profile-top")

    def test_returns_only_verified_active_sellers(
        self, api_client, seller_profile, another_seller_profile
    ):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        slugs = [s["slug"] for s in response.data["data"]]
        # seller_profile is unverified → not in top sellers
        assert seller_profile.slug not in slugs
        assert another_seller_profile.slug in slugs


class TestSellerProfilePictureView:
    url = reverse("seller-profile-picture")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.url, data={}, format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("apps.profiles.services.upload_file", return_value="profiles/pic.jpg")
    @patch("apps.profiles.services.delete_file")
    @patch(
        "apps.core.minio.get_public_url", return_value="http://minio/profiles/pic.jpg"
    )
    def test_seller_can_upload_profile_picture(
        self, mock_url, mock_delete, mock_upload, auth_client
    ):
        img = _make_real_image_upload()
        response = auth_client.post(self.url, data={"file": img}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_extension_returns_400(self, auth_client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        gif = SimpleUploadedFile("anim.gif", b"GIF89a", content_type="image/gif")
        response = auth_client.post(self.url, data={"file": gif}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSellerBannerImageView:
    url = reverse("seller-banner-image")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.url, data={}, format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("apps.profiles.services.upload_file", return_value="profiles/banner.jpg")
    @patch("apps.profiles.services.delete_file")
    @patch(
        "apps.core.minio.get_public_url",
        return_value="http://minio/profiles/banner.jpg",
    )
    def test_seller_can_upload_banner(
        self, mock_url, mock_delete, mock_upload, auth_client
    ):
        img = _make_real_image_upload(name="banner.jpg")
        response = auth_client.post(self.url, data={"file": img}, format="multipart")
        assert response.status_code == status.HTTP_200_OK


class TestSellerGovernmentIDView:
    url = reverse("seller-government-id")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.url, data={}, format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("apps.profiles.services.upload_file", return_value="profiles/gov-id.pdf")
    @patch("apps.profiles.services.delete_file")
    def test_seller_can_upload_government_id(
        self, mock_delete, mock_upload, auth_client
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        doc = SimpleUploadedFile("id.pdf", b"%PDF-data", content_type="application/pdf")
        response = auth_client.post(self.url, data={"file": doc}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

    def test_buyer_cannot_upload_government_id(self, buyer_client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        doc = SimpleUploadedFile("id.pdf", b"%PDF-data", content_type="application/pdf")
        response = buyer_client.post(self.url, data={"file": doc}, format="multipart")
        assert response.status_code == status.HTTP_403_FORBIDDEN
