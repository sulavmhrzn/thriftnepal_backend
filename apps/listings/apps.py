from django.apps import AppConfig


class ListingsConfig(AppConfig):
    name = "apps.listings"

    def ready(self):
        import apps.listings.signals  # noqa
