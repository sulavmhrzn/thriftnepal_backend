from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from apps.listings.models import Listing


@registry.register_document
class ListingDocument(Document):
    """
    Elasticsearch index for Listing model.
    """

    title = fields.TextField(
        analyzer="english",
        fields={
            "suggest": fields.TextField(analyzer="edge_ngram_analyzer"),
            "raw": fields.KeywordField(),
        },
    )

    description = fields.TextField(analyzer="english")

    condition = fields.KeywordField()

    status = fields.KeywordField()
    price = fields.FloatField()

    views_count = fields.IntegerField()

    is_negotiable = fields.BooleanField()
    accepts_meetup = fields.BooleanField()
    accepts_delivery = fields.BooleanField()

    category_name = fields.KeywordField()
    category_slug = fields.KeywordField()
    parent_category_name = fields.KeywordField()

    seller_id = fields.KeywordField()
    shop_name = fields.TextField(
        analyzer="english", fields={"raw": fields.KeywordField()}
    )
    is_verified_seller = fields.BooleanField()
    seller_province = fields.KeywordField()
    seller_city = fields.TextField(
        analyzer="english", fields={"raw": fields.KeywordField()}
    )
    has_images = fields.BooleanField()
    image_count = fields.IntegerField()

    class Index:
        name = "listings"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "edge_ngram_analyzer": {
                        "type": "custom",
                        "tokenizer": "edge_ngram_tokenizer",
                        "filter": ["lowercase"],
                    }
                },
                "tokenizer": {
                    "edge_ngram_tokenizer": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 20,
                        "token_chars": ["letter", "digit"],
                    }
                },
            },
        }

    class Django:
        model = Listing
        fields = [
            "id",
            "created_at",
            "updated_at",
        ]
        related_models = []

    def get_queryset(self):
        """
        Optimized queryset for bulk indexing.
        """
        return (
            Listing.all_objects.select_related(
                "seller",
                "seller__user",
                "category",
                "category__parent",
            )
            .prefetch_related("images")
            .filter(is_deleted=False)
        )

    def get_indexing_queryset(self):
        """
        Used for bulk indexing — populate + rebuild commands.
        Uses select_related only — no prefetch_related.
        Avoids iterator() + prefetch_related() conflict.
        prepare_has_images and prepare_image_count use
        separate queries per instance — acceptable for bulk indexing.
        """
        return Listing.all_objects.select_related(
            "seller",
            "seller__user",
            "category",
            "category__parent",
        ).filter(is_deleted=False)

    def prepare_category_name(self, instance) -> str | None:
        return instance.category.name if instance.category else None

    def prepare_category_slug(self, instance) -> str | None:
        return instance.category.slug if instance.category else None

    def prepare_parent_category_name(self, instance) -> str | None:
        if instance.category and instance.category.parent:
            return instance.category.parent.name
        return None

    def prepare_seller_id(self, instance) -> str:
        return str(instance.seller.id)

    def prepare_shop_name(self, instance) -> str:
        return instance.seller.shop_name

    def prepare_is_verified_seller(self, instance) -> bool:
        return instance.seller.is_verified_seller

    def prepare_seller_province(self, instance) -> str | None:
        return instance.seller.province

    def prepare_seller_city(self, instance) -> str | None:
        return instance.seller.city

    def prepare_has_images(self, instance) -> bool:
        return instance.images.exists()

    def prepare_image_count(self, instance) -> int:
        return instance.images.count()
