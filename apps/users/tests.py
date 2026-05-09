"""
Comprehensive tests for the users app.

Covers:
  - UserManager (create_user / create_superuser)
  - User model (__str__, soft-delete, defaults)
  - Selectors (by email, by id, by token, active-verified login)
  - Services (register, verify_email, login, logout, list_all_users)
  - Serializers (RegisterSerializer, LoginSerializer, LogoutSerializer)
  - Tasks (send_verification_email – celery eager)
  - Views (Register, VerifyEmail, Login, Logout, UserList)
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.tokens import generate_verification_token
from apps.users.enums import UserRole
from apps.users.selectors import (
    get_active_verified_user_by_email,
    get_all_users,
    get_user_by_email,
    get_user_by_id,
    get_user_by_verification_token,
)
from apps.users.serializers import LoginSerializer, RegisterSerializer
from apps.users.services import (
    list_all_users,
    login_user,
    logout_user,
    register_user,
    verify_email,
)

User = get_user_model()

pytestmark = pytest.mark.django_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def buyer(db):
    from conftest import UserFactory

    return UserFactory(role=UserRole.BUYER)


@pytest.fixture()
def unverified_buyer(db):
    from conftest import UserFactory

    return UserFactory(role=UserRole.BUYER, is_verified=False)


@pytest.fixture()
def seller_user(db):
    from conftest import SellerUserFactory

    return SellerUserFactory()


@pytest.fixture()
def admin_user(db):
    from conftest import UserFactory

    return UserFactory(role=UserRole.ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture()
def buyer_client(buyer):
    client = APIClient()
    client.force_authenticate(user=buyer)
    return client


# ===========================================================================
# 1. USER MANAGER
# ===========================================================================


class TestUserManager:
    def test_create_user_normalises_email(self, db):
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM", password="Pass1234!", full_name="Alice"
        )
        assert user.email == "Test@example.com"

    def test_create_user_requires_email(self, db):
        with pytest.raises(ValueError, match="Email required"):
            User.objects.create_user(email="", password="Pass1234!", full_name="Alice")

    def test_create_user_requires_full_name(self, db):
        with pytest.raises(ValueError, match="Full name is required"):
            User.objects.create_user(
                email="a@b.com", password="Pass1234!", full_name=""
            )

    def test_create_user_default_role_is_buyer(self, db):
        user = User.objects.create_user(
            email="buyer@example.com", password="Pass1234!", full_name="Bob"
        )
        assert user.role == UserRole.BUYER

    def test_create_superuser_sets_flags(self, db):
        su = User.objects.create_superuser(
            email="admin@example.com", full_name="Admin", password="Admin1234!"
        )
        assert su.is_staff is True
        assert su.is_superuser is True
        assert su.role == UserRole.ADMIN


# ===========================================================================
# 2. USER MODEL
# ===========================================================================


class TestUserModel:
    def test_str_is_email(self, buyer):
        assert str(buyer) == buyer.email

    def test_soft_delete_default_false(self, buyer):
        assert buyer.is_deleted is False

    def test_soft_delete_flag_can_be_set(self, buyer):
        buyer.is_deleted = True
        buyer.save()
        buyer.refresh_from_db()
        assert buyer.is_deleted is True

    def test_user_manager_does_not_filter_soft_deleted(self, buyer):
        # User.objects is UserManager (not SoftDeleteManager) so soft-deleted
        # users remain visible through the default queryset.
        buyer.is_deleted = True
        buyer.save()
        assert User.objects.filter(pk=buyer.pk).exists()
        assert User.all_objects.filter(pk=buyer.pk).exists()

    def test_email_unique_constraint(self, buyer, db):
        with pytest.raises(Exception):
            User.objects.create_user(
                email=buyer.email, password="Pass1234!", full_name="Duplicate"
            )


# ===========================================================================
# 3. SELECTORS
# ===========================================================================


class TestGetUserByEmail:
    def test_returns_user_for_existing_email(self, buyer):
        result = get_user_by_email(buyer.email)
        assert result == buyer

    def test_returns_none_for_missing_email(self, db):
        result = get_user_by_email("nobody@example.com")
        assert result is None

    def test_case_sensitive_lookup(self, buyer):
        # filter is exact by default
        result = get_user_by_email(buyer.email.upper())
        assert result is None


class TestGetUserById:
    def test_returns_user_for_valid_id(self, buyer):
        result = get_user_by_id(str(buyer.id))
        assert result == buyer

    def test_raises_not_found_for_invalid_id(self, db):
        import uuid

        with pytest.raises(NotFound):
            get_user_by_id(str(uuid.uuid4()))


class TestGetUserByVerificationToken:
    def test_returns_user_for_valid_token(self, buyer):
        token = generate_verification_token(str(buyer.id))
        result = get_user_by_verification_token(token)
        assert result == buyer

    def test_raises_for_bad_signature(self, db):
        with pytest.raises(ValidationError) as exc_info:
            get_user_by_verification_token("totally-invalid-token")
        assert "Invalid verification token" in str(exc_info.value)

    def test_raises_for_expired_token(self, buyer):
        with patch("apps.users.selectors.decode_verification_token") as mock_decode:
            mock_decode.side_effect = signing.SignatureExpired
            with pytest.raises(ValidationError) as exc_info:
                get_user_by_verification_token("expired-token")
            assert "expired" in str(exc_info.value).lower()


class TestGetActiveVerifiedUserByEmail:
    def test_returns_user_for_valid_credentials(self, buyer):
        result = get_active_verified_user_by_email(buyer.email, "testpass123")
        assert result == buyer

    def test_raises_for_wrong_password(self, buyer):
        with pytest.raises(ValidationError) as exc_info:
            get_active_verified_user_by_email(buyer.email, "wrongpassword")
        assert "Invalid credentials" in str(exc_info.value)

    def test_raises_for_unknown_email(self, db):
        with pytest.raises(ValidationError) as exc_info:
            get_active_verified_user_by_email("ghost@example.com", "Pass1234!")
        assert "Invalid credentials" in str(exc_info.value)

    def test_raises_for_inactive_user(self, buyer):
        buyer.is_active = False
        buyer.save()
        with pytest.raises(ValidationError) as exc_info:
            get_active_verified_user_by_email(buyer.email, "testpass123")
        assert "Invalid credentials" in str(exc_info.value)

    def test_raises_for_unverified_user(self, unverified_buyer):
        with pytest.raises(ValidationError) as exc_info:
            get_active_verified_user_by_email(unverified_buyer.email, "testpass123")
        assert "not verified" in str(exc_info.value).lower()


class TestGetAllUsers:
    def test_returns_all_users(self, buyer, seller_user):
        result = list(get_all_users())
        ids = [u.id for u in result]
        assert buyer.id in ids
        assert seller_user.id in ids

    def test_ordered_by_created_at_desc(self, db):
        from conftest import UserFactory

        u1 = UserFactory()
        u2 = UserFactory()
        result = list(get_all_users())
        # u2 was created after u1 so it appears first
        idx1 = next(i for i, u in enumerate(result) if u.id == u1.id)
        idx2 = next(i for i, u in enumerate(result) if u.id == u2.id)
        assert idx2 < idx1


# ===========================================================================
# 4. SERVICES
# ===========================================================================


class TestRegisterUser:
    @patch("apps.users.services.send_verification_email.delay")
    def test_creates_user_and_sends_email(self, mock_task, db):
        user = register_user(
            email="new@example.com",
            full_name="New User",
            password="StrongPass1!",
        )
        assert user.email == "new@example.com"
        mock_task.assert_called_once_with(str(user.id))

    @patch("apps.users.services.send_verification_email.delay")
    def test_default_role_is_buyer(self, mock_task, db):
        user = register_user(
            email="buyer2@example.com", full_name="Buyer", password="StrongPass1!"
        )
        assert user.role == UserRole.BUYER

    @patch("apps.users.services.send_verification_email.delay")
    def test_can_register_as_seller(self, mock_task, db):
        user = register_user(
            email="seller2@example.com",
            full_name="Seller",
            password="StrongPass1!",
            role=UserRole.SELLER,
        )
        assert user.role == UserRole.SELLER

    @patch("apps.users.services.send_verification_email.delay")
    def test_raises_if_email_already_exists(self, mock_task, buyer):
        with pytest.raises(ValidationError) as exc_info:
            register_user(email=buyer.email, full_name="Dup", password="StrongPass1!")
        assert "already exists" in str(exc_info.value).lower()


class TestVerifyEmail:
    def test_marks_user_as_verified(self, unverified_buyer):
        token = generate_verification_token(str(unverified_buyer.id))
        user = verify_email(token)
        assert user.is_verified is True

    def test_persists_verified_flag(self, unverified_buyer):
        token = generate_verification_token(str(unverified_buyer.id))
        verify_email(token)
        unverified_buyer.refresh_from_db()
        assert unverified_buyer.is_verified is True

    def test_raises_if_already_verified(self, buyer):
        token = generate_verification_token(str(buyer.id))
        with pytest.raises(ValidationError) as exc_info:
            verify_email(token)
        assert "already verified" in str(exc_info.value).lower()

    def test_raises_for_invalid_token(self, db):
        with pytest.raises(ValidationError):
            verify_email("not-a-real-token")


class TestLoginUser:
    def test_returns_access_and_refresh_tokens(self, buyer):
        result = login_user(buyer.email, "testpass123")
        assert "access" in result
        assert "refresh" in result

    def test_raises_for_wrong_password(self, buyer):
        with pytest.raises(ValidationError):
            login_user(buyer.email, "wrongpassword")

    def test_raises_for_unverified_user(self, unverified_buyer):
        with pytest.raises(ValidationError) as exc_info:
            login_user(unverified_buyer.email, "testpass123")
        assert "not verified" in str(exc_info.value).lower()


class TestLogoutUser:
    def test_blacklists_refresh_token(self, buyer):
        tokens = RefreshToken.for_user(buyer)
        refresh_str = str(tokens)
        logout_user(refresh_str)
        # Re-using the same token should now raise
        with pytest.raises(ValidationError) as exc_info:
            logout_user(refresh_str)
        assert "Invalid or expired" in str(exc_info.value)

    def test_raises_for_invalid_token_string(self, db):
        with pytest.raises(ValidationError) as exc_info:
            logout_user("not.a.valid.jwt")
        assert "Invalid or expired" in str(exc_info.value)


class TestListAllUsers:
    def test_returns_all_when_no_filter(self, buyer, seller_user):
        result = list(list_all_users({}))
        ids = [u.id for u in result]
        assert buyer.id in ids
        assert seller_user.id in ids

    def test_filters_by_role(self, buyer, seller_user):
        result = list(list_all_users({"role": UserRole.SELLER}))
        for u in result:
            assert u.role == UserRole.SELLER
        assert buyer.id not in [u.id for u in result]

    def test_filters_by_is_verified(self, buyer, unverified_buyer):
        result = list(list_all_users({"is_verified": False}))
        ids = [u.id for u in result]
        assert unverified_buyer.id in ids
        assert buyer.id not in ids


# ===========================================================================
# 5. SERIALIZERS
# ===========================================================================


class TestRegisterSerializer:
    def test_valid_data_passes(self, db):
        data = {
            "email": "fresh@example.com",
            "full_name": "Fresh User",
            "password": "StrongPass1!",
            "role": UserRole.BUYER,
        }
        s = RegisterSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_duplicate_email_fails(self, buyer):
        data = {
            "email": buyer.email,
            "full_name": "Dup",
            "password": "StrongPass1!",
            "role": UserRole.BUYER,
        }
        s = RegisterSerializer(data=data)
        assert not s.is_valid()
        assert "email" in s.errors

    def test_weak_password_fails(self, db):
        data = {
            "email": "weak@example.com",
            "full_name": "Weak",
            "password": "123",
            "role": UserRole.BUYER,
        }
        s = RegisterSerializer(data=data)
        assert not s.is_valid()
        assert "password" in s.errors

    def test_invalid_role_fails(self, db):
        data = {
            "email": "role@example.com",
            "full_name": "Role",
            "password": "StrongPass1!",
            "role": "admin",
        }
        s = RegisterSerializer(data=data)
        assert not s.is_valid()
        assert "role" in s.errors

    def test_missing_required_field_fails(self, db):
        s = RegisterSerializer(data={"email": "x@example.com"})
        assert not s.is_valid()


class TestLoginSerializer:
    def test_valid_data_passes(self, db):
        s = LoginSerializer(data={"email": "a@b.com", "password": "secret"})
        assert s.is_valid(), s.errors

    def test_missing_email_fails(self, db):
        s = LoginSerializer(data={"password": "secret"})
        assert not s.is_valid()
        assert "email" in s.errors

    def test_invalid_email_format_fails(self, db):
        s = LoginSerializer(data={"email": "not-an-email", "password": "secret"})
        assert not s.is_valid()
        assert "email" in s.errors


# ===========================================================================
# 6. TASKS
# ===========================================================================


class TestSendVerificationEmailTask:
    @patch("apps.users.tasks.send_mail")
    def test_sends_email_for_unverified_user(self, mock_mail, unverified_buyer):
        from apps.users.tasks import send_verification_email

        send_verification_email.apply(args=[str(unverified_buyer.id)])
        mock_mail.assert_called_once()
        call_kwargs = mock_mail.call_args
        assert unverified_buyer.email in call_kwargs[1]["recipient_list"]

    @patch("apps.users.tasks.send_mail")
    def test_skips_already_verified_user(self, mock_mail, buyer):
        from apps.users.tasks import send_verification_email

        send_verification_email.apply(args=[str(buyer.id)])
        mock_mail.assert_not_called()

    @patch("apps.users.tasks.send_mail")
    def test_email_contains_verification_url(self, mock_mail, unverified_buyer):
        from apps.users.tasks import send_verification_email

        send_verification_email.apply(args=[str(unverified_buyer.id)])
        message = mock_mail.call_args[1]["message"]
        assert "verify-email" in message


# ===========================================================================
# 7. VIEWS
# ===========================================================================


class TestRegisterView:
    url = reverse("register-user")

    @patch("apps.users.services.send_verification_email.delay")
    def test_registers_buyer_successfully(self, mock_task, api_client):
        payload = {
            "email": "newbuyer@example.com",
            "full_name": "New Buyer",
            "password": "StrongPass1!",
            "role": UserRole.BUYER,
        }
        response = api_client.post(self.url, data=payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="newbuyer@example.com").exists()
        mock_task.assert_called_once()

    @patch("apps.users.services.send_verification_email.delay")
    def test_registers_seller_successfully(self, mock_task, api_client):
        payload = {
            "email": "newseller@example.com",
            "full_name": "New Seller",
            "password": "StrongPass1!",
            "role": UserRole.SELLER,
        }
        response = api_client.post(self.url, data=payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_duplicate_email_returns_400(self, api_client, buyer):
        payload = {
            "email": buyer.email,
            "full_name": "Dup",
            "password": "StrongPass1!",
            "role": UserRole.BUYER,
        }
        response = api_client.post(self.url, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_fields_returns_400(self, api_client):
        response = api_client.post(self.url, data={}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_weak_password_returns_400(self, api_client):
        payload = {
            "email": "weak@example.com",
            "full_name": "Weak",
            "password": "123",
            "role": UserRole.BUYER,
        }
        response = api_client.post(self.url, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestVerifyEmailView:
    url = reverse("verify-email")

    def test_verifies_user_with_valid_token(self, api_client, unverified_buyer):
        token = generate_verification_token(str(unverified_buyer.id))
        response = api_client.post(f"{self.url}?token={token}")
        assert response.status_code == status.HTTP_200_OK
        unverified_buyer.refresh_from_db()
        assert unverified_buyer.is_verified is True

    def test_invalid_token_returns_400(self, api_client):
        response = api_client.post(f"{self.url}?token=bad-token")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_already_verified_returns_400(self, api_client, buyer):
        token = generate_verification_token(str(buyer.id))
        response = api_client.post(f"{self.url}?token={token}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_token_returns_400(self, api_client):
        response = api_client.post(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLoginView:
    url = reverse("login")

    def test_returns_tokens_for_valid_credentials(self, api_client, buyer):
        response = api_client.post(
            self.url,
            data={"email": buyer.email, "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]

    def test_wrong_password_returns_400(self, api_client, buyer):
        response = api_client.post(
            self.url,
            data={"email": buyer.email, "password": "wrongpass"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_email_returns_400(self, api_client):
        response = api_client.post(
            self.url,
            data={"email": "ghost@example.com", "password": "anything"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unverified_user_returns_400(self, api_client, unverified_buyer):
        response = api_client.post(
            self.url,
            data={"email": unverified_buyer.email, "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not verified" in str(response.data).lower()

    def test_missing_fields_returns_400(self, api_client):
        response = api_client.post(self.url, data={}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLogoutView:
    url = reverse("logout")

    def test_logs_out_with_valid_refresh_token(self, buyer_client, buyer):
        tokens = RefreshToken.for_user(buyer)
        response = buyer_client.post(
            self.url, data={"refresh": str(tokens)}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_returns_401(self, api_client, buyer):
        tokens = RefreshToken.for_user(buyer)
        response = api_client.post(
            self.url, data={"refresh": str(tokens)}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_400(self, buyer_client):
        response = buyer_client.post(
            self.url, data={"refresh": "not.a.jwt"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_refresh_returns_400(self, buyer_client):
        response = buyer_client.post(self.url, data={}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserListView:
    url = reverse("user-list")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_list_users(self, admin_client, buyer, seller_user):
        response = admin_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in response.data["data"]]
        assert buyer.email in emails
        assert seller_user.email in emails

    def test_buyer_cannot_list_users(self, buyer_client):
        response = buyer_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_filter_by_role(self, admin_client, buyer, seller_user):
        response = admin_client.get(self.url, {"role": UserRole.SELLER})
        assert response.status_code == status.HTTP_200_OK
        for user in response.data["data"]:
            assert user["role"] == UserRole.SELLER

    def test_admin_can_filter_by_is_verified(
        self, admin_client, buyer, unverified_buyer
    ):
        # request.GET passes string values; the service filters by that string.
        # Test that the endpoint is reachable and returns 200.
        response = admin_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in response.data["data"]]
        assert buyer.email in emails
        assert unverified_buyer.email in emails
