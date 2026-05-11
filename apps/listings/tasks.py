import structlog
from celery import shared_task

from apps.listings.selectors import get_listing_by_id_for_indexing

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="elasticsearch",
)
def index_listing_task(self, listing_id: str) -> None:
    try:
        from apps.listings.documents import ListingDocument

        listing = get_listing_by_id_for_indexing(listing_id)
        if listing.is_deleted:
            try:
                ListingDocument.get(id=listing_id).delete()
                logger.info(
                    "listing_removed_from_es",
                    listing_id=listing_id,
                )
            except Exception:
                pass
            return
        ListingDocument().update(listing)
        logger.info(
            "listing_indexed",
            listing_id=listing_id,
            status=listing.status,
        )
    except Exception as exc:
        logger.error(
            "listing_index_failed",
            listing_id=listing_id,
            error=str(exc),
            retries=self.request.retries,
        )
        raise self.retry(
            exc=exc,
            countdown=5 * (2**self.request.retries),
        )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="elasticsearch",
)
def remove_listing_from_index_task(self, listing_id: str) -> None:
    try:
        from apps.listings.documents import ListingDocument

        try:
            ListingDocument.get(id=listing_id).delete()
            logger.info("listing_removed_from_es", listing_id=listing_id)
        except Exception:
            pass
    except Exception as exc:
        logger.error(
            "listing_remove_failed",
            listing_id=listing_id,
            error=str(exc),
        )
        raise self.retry(
            exc=exc,
            countdown=5 * (2**self.request.retries),
        )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="elasticsearch",
)
def bulk_index_listings_task(self, listing_ids: list[str]) -> None:
    try:
        from apps.listings.documents import ListingDocument
        from apps.listings.selectors import get_listings_by_ids

        listings = get_listings_by_ids(listing_ids)
        for listing in listings:
            ListingDocument().update(listing)

        logger.info(
            "bulk_listing_indexed",
            count=len(listing_ids),
        )
    except Exception as exc:
        logger.error(
            "bulk_index_failed",
            listing_ids=listing_ids,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=10)
