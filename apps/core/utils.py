def soft_delete(instance):
    """
    Soft delete any BaseModel instance.
    """
    instance.is_deleted = True
    instance.save(update_fields=["is_deleted", "updated_at"])
