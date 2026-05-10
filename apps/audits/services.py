from curses import meta

import structlog

from apps.audits.models import BusinessEvent

logger = structlog.get_logger(__name__)


def create_business_event(
    action: str,
    user=None,
    metadata: dict = None,
    request=None,
):
    ip_address = None
    request_id = None

    if request:
        ip_address = _get_client_ip(request)

    try:
        context = structlog.contextvars.get_merged_contextvars(structlog.get_logger())
        request_id = context.get("request_id")
    except Exception:
        pass

    event = BusinessEvent.objects.create(
        action=action,
        user=user,
        metadata=metadata or {},
        ip_address=ip_address,
        request_id=request_id,
    )
    logger.info(
        "business_event_created",
        action=action,
        user_id=str(user.id) if user else None,
        metadata=meta,
    )

    return event


def _get_client_ip(request):
    forwaded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwaded_for:
        return forwaded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
