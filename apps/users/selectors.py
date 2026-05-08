from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.tokens import decode_verification_token

User = get_user_model()


def get_user_by_email(email):
    return User.objects.filter(email=email).first()


def get_user_by_id(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise NotFound("User not found")


def get_user_by_verification_token(token: str):
    try:
        user_id = decode_verification_token(token)
        return get_user_by_id(user_id)
    except signing.SignatureExpired:
        raise ValidationError(
            {"non_field_errors": ["Verification link expired. Request a new one."]}
        )
    except signing.BadSignature:
        raise ValidationError({"non_field_errors": ["Invalid verification token."]})


def get_active_verified_user_by_email(email, password):
    user = get_user_by_email(email)
    if not user or not user.check_password(password):
        raise ValidationError({"non_field_errors": ["Invalid credentials"]})
    if not user.is_active:
        raise ValidationError({"non_field_errors": ["Invalid credentials"]})
    if not user.is_verified:
        raise ValidationError(
            {"non_field_errors": ["User is not verified. Please check your inbox."]}
        )
    return user


def get_all_users():
    return User.objects.all().order_by("-created_at")
