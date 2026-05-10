import structlog
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audits.services import create_business_event
from apps.users.enums import UserRole
from apps.users.selectors import (
    get_active_verified_user_by_email,
    get_all_users,
    get_user_by_email,
    get_user_by_verification_token,
)
from apps.users.tasks import send_verification_email

User = get_user_model()
logger = structlog.get_logger(__name__)


def register_user(email, full_name, password, role=UserRole.BUYER):
    exists = get_user_by_email(email)
    if exists:
        raise ValidationError(
            {"non_field_errors": ["User with this email already exists"]}
        )
    user = User.objects.create_user(
        email=email, full_name=full_name, password=password, role=role
    )
    logger.info(
        "user_registered",
        user_id=str(user.id),
        role=user.role,
    )

    send_verification_email.delay(str(user.id))
    return user


def verify_email(token: str):
    user = get_user_by_verification_token(token)

    if user.is_verified:
        raise ValidationError({"non_field_errors": ["Account already verified."]})

    user.is_verified = True
    user.save(update_fields=["is_verified", "updated_at"])
    logger.info(
        "email_verified",
        user_id=str(user.id),
    )

    return user


def login_user(email, password, request=None):
    try:
        user = get_active_verified_user_by_email(email, password)

    except ValidationError:
        create_business_event(
            action="user_login_failed",
            metadata={"email": email},
            request=request,
        )
        raise
    tokens = RefreshToken.for_user(user)
    create_business_event(
        action="user_logged_in",
        user=user,
        request=request,
    )
    return {"access": str(tokens.access_token), "refresh": tokens}


def logout_user(refresh_token):
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info("user_logged_out")
    except TokenError:
        raise ValidationError(
            {"non_field_errors": ["Invalid or expired refresh token."]}
        )


def list_all_users(filters):
    users = get_all_users()
    if filters.get("role"):
        users = users.filter(role=filters["role"])
    if filters.get("is_verified") is not None:
        users = users.filter(is_verified=filters["is_verified"])
    return users
