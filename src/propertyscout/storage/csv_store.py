
import csv
from dataclasses import asdict
from pathlib import Path

from propertyscout.models import PropertyListing


EXPORT_DIR = Path("data/exports")
EXPORT_FILE = EXPORT_DIR / "properties.csv"


def save_properties(
    listings: list[PropertyListing],
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    unique_listings: list[PropertyListing] = []
    seen_urls: set[str] = set()

    for listing in listings:
        if not listing.listing_id or not listing.title:
            raise ValueError("Listing ID and title are required.")

        if listing.unit_price < 0 or listing.size_sqft <= 0:
            raise ValueError(
                f"Invalid price or area: {listing.listing_id}"
            )

        if listing.source_url in seen_urls:
            continue

        seen_urls.add(listing.source_url)
        unique_listings.append(listing)

    if not unique_listings:
        raise ValueError("No valid property listings to export.")

    rows = []

    for listing in unique_listings:
        row = asdict(listing)
        row["price_per_sqft"] = listing.price_per_sqft
        rows.append(row)

    fieldnames = list(rows[0].keys())

    with EXPORT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} listings to {EXPORT_FILE.resolve()}")
    return EXPORT_FILE
