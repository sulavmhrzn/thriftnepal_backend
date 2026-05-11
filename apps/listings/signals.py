from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.listings.models import Listing


@receiver(post_save, sender=Listing)
def sync_listing_to_elasticsearch(sender, instance, **kwargs):
    from apps.listings.tasks import index_listing_task, remove_listing_from_index_task

    if instance.is_deleted:
        transaction.on_commit(
            lambda: remove_listing_from_index_task.delay(str(instance.id))
        )
    else:
        transaction.on_commit(lambda: index_listing_task.delay(str(instance.id)))
