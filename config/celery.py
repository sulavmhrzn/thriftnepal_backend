import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.task_routes = {
    "apps.listings.tasks.index_listing_task": {
        "queue": "elasticsearch",
    },
    "apps.listings.tasks.remove_listing_from_index_task": {
        "queue": "elasticsearch",
    },
    "apps.listings.tasks.bulk_index_listings_task": {
        "queue": "elasticsearch",
    },
    "apps.users.tasks.send_verification_email": {
        "queue": "email",
    },
}

app.conf.task_default_queue = "default"
