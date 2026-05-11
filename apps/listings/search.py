import structlog
from elasticsearch.dsl import A, Q

from apps.listings.documents import ListingDocument
from apps.listings.selectors import get_listings_by_ids

logger = structlog.get_logger(__name__)


DEFAULT_PAGE_SIZE = 20

PRICE_RANGES = [
    {"key": "under_1000", "to": 1000},
    {"key": "1000_to_5000", "from": 1000, "to": 5000},
    {"key": "5000_to_20000", "from": 5000, "to": 20000},
    {"key": "above_20000", "from": 20000},
]


def search_listings(
    query: str = None,
    filters: dict = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """
    Main search function. Builds ES query, executes, returns results + facets.
    """
    filters = filters or {}

    search = ListingDocument.search()

    if query:
        text_query = Q(
            "multi_match",
            query=query,
            fields=[
                "title^3",
                "description^1",
                "shop_name^2",
                "category_name^1.5",
            ],
            fuzziness="AUTO",
            minimum_should_match="75%",
        )
        search = search.query(text_query)
    else:
        search = search.query("match_all")

    search = search.filter("term", status="active")
    search = search.filter("term", has_images=True)

    if condition := filters.get("condition"):
        search = search.filter("term", condition=condition)

    if category_slug := filters.get("category_slug"):
        search = search.filter("term", category_slug=category_slug)

    if min_price := filters.get("min_price"):
        search = search.filter("range", price={"gte": float(min_price)})

    if max_price := filters.get("max_price"):
        search = search.filter("range", price={"lte": float(max_price)})

    if filters.get("is_negotiable") is not None:
        search = search.filter("term", is_negotiable=filters["is_negotiable"])

    if filters.get("accepts_meetup") is not None:
        search = search.filter("term", accepts_meetup=filters["accepts_meetup"])

    if filters.get("accepts_delivery") is not None:
        search = search.filter("term", accepts_delivery=filters["accepts_delivery"])

    if province := filters.get("seller_province"):
        search = search.filter("term", seller_province=province)

    if filters.get("is_verified_seller") is not None:
        search = search.filter("term", is_verified_seller=filters["is_verified_seller"])

    search.aggs.bucket("by_condition", A("terms", field="condition", size=10))

    search.aggs.bucket("by_category", A("terms", field="category_slug", size=20))

    search.aggs.bucket("by_price_range", A("range", field="price", ranges=PRICE_RANGES))

    search.aggs.bucket("by_province", A("terms", field="seller_province", size=10))

    if query:
        search = search.sort("_score", "-created_at")
    else:
        search = search.sort("-created_at")

    offset = (page - 1) * page_size
    search = search[offset : offset + page_size]

    try:
        response = search.execute()
    except Exception as e:
        logger.error("elasticsearch_search_failed", error=str(e))
        raise

    listing_ids = [hit.id for hit in response.hits]

    listings = get_listings_by_ids(listing_ids)

    facets = _extract_facets(response)

    total = response.hits.total.value
    pages = (total + page_size - 1) // page_size

    logger.info(
        "search_executed",
        query=query,
        filters=filters,
        total=total,
        page=page,
    )

    return {
        "listings": listings,
        "total": total,
        "facets": facets,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


def _extract_facets(response) -> dict:
    """
    Extracts aggregation results from ES response.
    Transforms ES bucket format into clean dict for API response.
    """
    facets = {}

    # condition facet
    if hasattr(response.aggregations, "by_condition"):
        facets["conditions"] = [
            {
                "value": bucket.key,
                "count": bucket.doc_count,
            }
            for bucket in response.aggregations.by_condition.buckets
        ]

    # category facet
    if hasattr(response.aggregations, "by_category"):
        facets["categories"] = [
            {
                "value": bucket.key,
                "count": bucket.doc_count,
            }
            for bucket in response.aggregations.by_category.buckets
        ]

    # price range facet
    if hasattr(response.aggregations, "by_price_range"):
        facets["price_ranges"] = [
            {
                "key": PRICE_RANGES[i].get("key", f"range_{i}"),
                "count": bucket.doc_count,
                "from": getattr(bucket, "from", None),
                "to": getattr(bucket, "to", None),
            }
            for i, bucket in enumerate(response.aggregations.by_price_range.buckets)
        ]

    # province facet
    if hasattr(response.aggregations, "by_province"):
        facets["provinces"] = [
            {
                "value": bucket.key,
                "count": bucket.doc_count,
            }
            for bucket in response.aggregations.by_province.buckets
            if bucket.key  # skip null province
        ]

    return facets
