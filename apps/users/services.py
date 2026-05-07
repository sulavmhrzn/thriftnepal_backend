from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.enums import UserRole
from apps.users.selectors import (
    get_active_verified_user_by_email,
    get_user_by_email,
    get_user_by_verification_token,
)
from apps.users.tasks import send_verification_email

User = get_user_model()


def register_user(email, full_name, password, role=UserRole.BUYER):
    exists = get_user_by_email(email)
    if exists:
        raise ValidationError("User with this email already exists")
    user = User.objects.create_user(
        email=email, full_name=full_name, password=password, role=role
    )
    send_verification_email.delay(str(user.id))
    return user


def verify_email(token: str):
    user = get_user_by_verification_token(token)

    if user.is_verified:
        raise ValidationError("Account already verified.")

    user.is_verified = True
    user.save(update_fields=["is_verified", "updated_at"])
    return user


def login_user(email, password):
    user = get_active_verified_user_by_email(email, password)
    tokens = RefreshToken.for_user(user)
    return {"access": str(tokens.access_token), "refresh": tokens}


def logout_user(refresh_token):
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        raise ValidationError("Invalid or expired refresh token.")
