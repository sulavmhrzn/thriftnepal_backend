from django.utils.text import slugify


def soft_delete(instance):
    """
    Soft delete any BaseModel instance.
    """
    instance.is_deleted = True
    instance.save(update_fields=["is_deleted", "updated_at"])


def generate_unique_slug(text, model_class):
    """
    Generates unque slug for any model
    """
    base_slug = slugify(text)
    slug = base_slug
    counter = 1

    while model_class.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug
