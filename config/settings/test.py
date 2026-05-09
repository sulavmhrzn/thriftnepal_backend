"""
Test settings — uses in-memory SQLite, disables external services.
"""

from .base import *  # noqa: F401, F403

SECRET_KEY = "django-insecure-#8f5c47^*x@&ewh5el0m)((ojgz4iwq*+0a^1u=)2gssj665^c"
DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Dummy MinIO settings to satisfy imports (mocked in tests)
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "test-access-key"
MINIO_SECRET_KEY = "test-secret-key"
MINIO_PUBLIC_BUCKET = "public"
MINIO_PRIVATE_BUCKET = "private"
MINIO_USE_SSL = False

FRONTEND_BASE_URL = "http://localhost:3000"
DEFAULT_FROM_EMAIL = "test@thriftnepal.com"

# Disable celery during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Suppress email sending
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
