"""Safely import authorized rental listing CSV files into PropertyScout."""

import argparse
import csv
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from propertyscout.rentals import csv_store
from propertyscout.rentals.models import RentalListing, RentalListingCreate


OPTIONAL_FIELDS = {
    "bedrooms",
    "area_sqft",
    "external_listing_id",
    "advertised_date",
    "last_seen_date",
    "availability_checked_date",
    "contact_reference",
}

REQUIRED_HEADERS = {
    "title",
    "emirate",
    "property_type",
    "community",
    "annual_rent_aed",
    "source_name",
    "source_url",
}


def normalize_row(row: dict) -> dict:
    """Convert blank optional CSV cells to None."""
    cleaned = {}

    for key, value in row.items():
        if key is None:
            continue

        if isinstance(value, str):
            value = value.strip()

        if key in OPTIONAL_FIELDS and value == "":
            value = None

        cleaned[key] = value

    return cleaned


def source_key(listing) -> tuple[str, str]:
    """Identify a listing by its source and external ID."""
    return (
        listing.source_name.strip().casefold(),
        listing.external_listing_id.strip(),
    )


def url_key(listing) -> tuple[str, str]:
    """Fallback duplicate check for listings without a source ID."""
    return (
        listing.source_name.strip().casefold(),
        str(listing.source_url).rstrip("/").casefold(),
    )


def import_csv(csv_path: Path, apply_changes: bool = False) -> int:
    if not csv_path.is_file():
        print(f"ERROR: CSV file not found: {csv_path}")
        return 1

    try:
        with csv_path.open(
            "r", newline="", encoding="utf-8-sig"
        ) as file:
            reader = csv.DictReader(file)

            headers = set(reader.fieldnames or [])
            missing = REQUIRED_HEADERS - headers

            if missing:
                print("ERROR: Missing required CSV columns:")
                for header in sorted(missing):
                    print(f"  - {header}")
                return 1

            existing = csv_store.load_rentals()
            merged: list[RentalListing] = list(existing)

            known_ids = {
                source_key(item)
                for item in existing
                if item.external_listing_id
            }
            known_urls = {url_key(item) for item in existing}

            accepted = 0
            duplicates = 0
            rejected = 0
            seen_rows = 0

            for line_number, row in enumerate(reader, start=2):
                if not row or not any(
                    str(value or "").strip() for value in row.values()
                ):
                    continue

                seen_rows += 1
                cleaned = normalize_row(row)

                try:
                    payload = RentalListingCreate.model_validate(cleaned)
                except ValidationError as exc:
                    rejected += 1
                    print(f"\nREJECTED row {line_number}:")
                    for error in exc.errors():
                        field = ".".join(
                            str(part) for part in error["loc"]
                        )
                        print(f"  {field}: {error['msg']}")
                    continue

                if payload.external_listing_id:
                    key = source_key(payload)
                    if key in known_ids:
                        duplicates += 1
                        print(
                            f"SKIPPED row {line_number}: duplicate source "
                            f"ID {payload.external_listing_id!r} "
                            f"from {payload.source_name!r}"
                        )
                        continue

                url = url_key(payload)
                if url in known_urls:
                    duplicates += 1
                    print(
                        f"SKIPPED row {line_number}: source URL already "
                        f"imported ({payload.source_url})"
                    )
                    continue

                listing = RentalListing(
                    id=str(uuid4()),
                    **payload.model_dump(),
                )
                merged.append(listing)
                accepted += 1
                known_urls.add(url)

                if payload.external_listing_id:
                    known_ids.add(source_key(payload))

    except (OSError, csv.Error) as exc:
        print(f"ERROR reading CSV: {exc}")
        return 1

    print("\n--- PropertyScout Rental Import Report ---")
    print(f"Input file:          {csv_path}")
    print(f"Rows examined:       {seen_rows}")
    print(f"Existing listings:   {len(existing)}")
    print(f"New valid listings:  {accepted}")
    print(f"Duplicates skipped:  {duplicates}")
    print(f"Invalid rows:        {rejected}")
    print(f"Listings after run:  {len(merged)}")

    if not apply_changes:
        print("\nDRY RUN: Nothing was saved.")
        print("Review the report, then rerun with --apply to save.")
        return 0

    if accepted == 0:
        print("\nNothing new to import. Existing data was not rewritten.")
        return 0

    try:
        output_path = csv_store.save_rentals(merged)
    except (OSError, ValueError) as exc:
        print(f"\nERROR saving listings: {exc}")
        print("The import did not complete successfully.")
        return 1

    print(f"\nSUCCESS: Saved {accepted} new listings.")
    print(f"Rental data file: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import an authorized rental listing CSV."
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to the provider CSV export",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Save accepted listings; without this flag, run a dry run",
    )
    args = parser.parse_args()

    return import_csv(args.csv_file, apply_changes=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
