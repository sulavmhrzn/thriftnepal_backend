from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.core.tokens import generate_verification_token


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id: str):
    try:
        from apps.users.selectors import get_user_by_id

        user = get_user_by_id(user_id)

        if user.is_verified:
            return

        token = generate_verification_token(str(user.id))
        verify_url = f"{settings.FRONTEND_BASE_URL}/verify-email/?token={token}"

        send_mail(
            subject="Verify your ThriftNepal account",
            message=f"Click to verify your account: {verify_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
