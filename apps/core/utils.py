import uuid

from django.utils.text import slugify


def soft_delete(instance):
    """
    Soft delete any BaseModel instance.
    """
    instance.is_deleted = True
    instance.save(update_fields=["is_deleted", "updated_at"])


def generate_unique_slug(name: str) -> str:
    """
    Generates slug from name + 8 char UUID suffix.
    """
    base_slug = slugify(name)
    unique_suffix = str(uuid.uuid4())[:8]
    return f"{base_slug}-{unique_suffix}"
