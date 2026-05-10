from auditlog.registry import auditlog
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.core.models import BaseModel
from apps.users.enums import UserRole


class UserManager(BaseUserManager):
    def create_user(
        self, email, password, full_name, role=UserRole.BUYER, **extra_fields
    ):
        if not email:
            raise ValueError("Email required")

        if not full_name:
            raise ValueError("Full name is required")

        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=False)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.BUYER,
    )
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return self.email


auditlog.register(
    User,
    exclude_fields=[
        "password",
        "updated_at",
        "last_login",
    ],
)
