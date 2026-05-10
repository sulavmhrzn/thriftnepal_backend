from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.users.enums import UserRole
from apps.users.models import User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                User.objects.all(),
                lookup="iexact",
                message="User with this email already exists",
            ),
        ]
    )
    full_name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[UserRole.BUYER, UserRole.SELLER])

    def validate_password(self, value):
        django_validate_password(value)
        return value


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserListSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    is_verified = serializers.BooleanField()
    is_deleted = serializers.BooleanField()
