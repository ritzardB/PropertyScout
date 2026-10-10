
from typing import Any

from propertyscout.models import PropertyListing


def normalize_property(
    record: dict[str, Any],
    *,
    source_name: str,
) -> PropertyListing:
    """Convert a provider-normalized record into PropertyScout's model.

    This function expects normalized field names, not a provider's
    raw JSON response. A provider-specific mapper should translate
    its response into these fields first.
    """
    return PropertyListing(
        listing_id=str(record["listing_id"]),
        title=str(record["title"]),
        property_type=str(record["property_type"]).lower(),
        transaction_type=str(record["transaction_type"]).lower(),
        emirate=str(record["emirate"]),
        area=str(record["area"]),
        unit_price=float(record["unit_price"]),
        size_sqft=float(record["size_sqft"]),
        source_name=source_name,
        source_url=str(record["source_url"]),
        price_period=str(record["price_period"]).lower(),
        bedrooms=record.get("bedrooms"),
        project_status=record.get("project_status"),
    )
