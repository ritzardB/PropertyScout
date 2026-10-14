
"""Persistent CSV storage for rental listings."""

import csv
import os
import tempfile
from pathlib import Path

from propertyscout.rentals.models import RentalListing


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RENTAL_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RENTAL_DATA_FILE = RENTAL_DATA_DIR / "rental_listings.csv"

FIELDNAMES = list(RentalListing.model_fields.keys())

OPTIONAL_FIELDS = {
    "bedrooms",
    "area_sqft",
    "description",
    "source_url",
    "external_listing_id",
    "advertised_date",
    "last_seen_date",
    "availability_checked_date",
    "contact_reference",
    "private_notes",
}


def load_rentals() -> list[RentalListing]:
    """Load persisted listings, supplying defaults for older CSV columns."""
    if not RENTAL_DATA_FILE.exists():
        return []

    listings: list[RentalListing] = []

    with RENTAL_DATA_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        for original_row in reader:
            row = dict(original_row)

            for field in OPTIONAL_FIELDS:
                if row.get(field) == "":
                    row[field] = None

            # Legacy CSV records may not contain newer fields.
            if not row.get("source_name"):
                row["source_name"] = "Personal Collection"

            if not row.get("listing_origin"):
                row["listing_origin"] = "Personal Collection"

            listings.append(RentalListing.model_validate(row))

    return listings


def save_rentals(listings: list[RentalListing]) -> Path:
    """Atomically replace the rental CSV after checking for duplicate IDs."""
    data_dir = RENTAL_DATA_FILE.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    seen_ids: set[str] = set()
    seen_source_ids: set[tuple[str, str]] = set()

    for listing in listings:
        if listing.id in seen_ids:
            raise ValueError(f"Duplicate rental ID: {listing.id}")
        seen_ids.add(listing.id)

        if listing.external_listing_id:
            source_key = (
                listing.source_name.casefold(),
                listing.external_listing_id,
            )
            if source_key in seen_source_ids:
                raise ValueError(
                    "Duplicate source listing ID: "
                    f"{listing.external_listing_id}"
                )
            seen_source_ids.add(source_key)

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=data_dir,
            delete=False,
            suffix=".tmp",
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()

            for listing in listings:
                writer.writerow(listing.model_dump(mode="json"))

        os.replace(temporary_path, RENTAL_DATA_FILE)

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    return RENTAL_DATA_FILE
