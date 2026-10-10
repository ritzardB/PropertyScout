
import csv

import pytest

from propertyscout.models import PropertyListing
from propertyscout.storage import csv_store


def make_listing(**overrides):
    data = {
        "listing_id": "TEST-001",
        "title": "Test Apartment",
        "property_type": "residential",
        "transaction_type": "sale",
        "emirate": "Abu Dhabi",
        "area": "Al Reem Island",
        "unit_price": 1_500_000,
        "size_sqft": 1200,
        "source_name": "test",
        "source_url": "https://example.com/listing/1",
    }
    data.update(overrides)
    return PropertyListing(**data)


def test_sale_price_per_sqft():
    listing = make_listing()
    assert listing.price_per_sqft == 1250.00


def test_annual_rent_price_per_sqft():
    listing = make_listing(
        transaction_type="rent",
        price_period="year",
        unit_price=180_000,
        size_sqft=1500,
    )
    assert listing.price_per_sqft == 120.00
    assert listing.price_label == "Rent per year"


def test_monthly_rent_is_supported():
    listing = make_listing(
        transaction_type="rent",
        price_period="month",
        unit_price=10_000,
        size_sqft=1000,
    )
    assert listing.price_label == "Rent per month"


def test_rent_requires_a_valid_period():
    with pytest.raises(ValueError):
        make_listing(transaction_type="rent")


def test_sale_cannot_use_monthly_period():
    with pytest.raises(ValueError):
        make_listing(price_period="month")


def test_negative_price_is_rejected():
    with pytest.raises(ValueError):
        make_listing(unit_price=-100)


def test_invalid_size_is_rejected():
    with pytest.raises(ValueError):
        make_listing(size_sqft=0)


def test_csv_export_and_duplicate_urls(tmp_path, monkeypatch):
    output_file = tmp_path / "properties.csv"

    monkeypatch.setattr(csv_store, "EXPORT_DIR", tmp_path)
    monkeypatch.setattr(csv_store, "EXPORT_FILE", output_file)

    first = make_listing()
    duplicate = make_listing(
        listing_id="TEST-002",
        title="Duplicate Listing",
    )

    saved_path = csv_store.save_properties([first, duplicate])

    assert saved_path == output_file

    with output_file.open(
        newline="", encoding="utf-8-sig"
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["listing_id"] == "TEST-001"
    assert float(rows[0]["price_per_sqft"]) == 1250.00
