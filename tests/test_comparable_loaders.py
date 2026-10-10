
import csv

import pytest

from propertyscout.comparables.loaders import load_dld


FIELDS = [
    "transaction_number",
    "transaction_date",
    "transaction_group",
    "is_offplan",
    "usage",
    "property_type",
    "property_sub_type",
    "rooms",
    "transaction_value_aed",
    "area_used_sqft",
    "area",
    "project",
    "master_project",
    "source",
]


def write_dld_csv(tmp_path, records):
    path = tmp_path / "dld_test.csv"

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return path


def make_row(**overrides):
    row = {
        "transaction_number": "TX-001",
        "transaction_date": "2026-09-01",
        "transaction_group": "Sales",
        "is_offplan": "Ready",
        "usage": "Residential",
        "property_type": "Unit",
        "property_sub_type": "Flat",
        "transaction_value_aed": "1000000",
        "area_used_sqft": "500",
        "area": "Business Bay",
        "project": "Example Tower",
        "master_project": "",
        "source": "DLD",
    }
    row.update(overrides)
    return row


def test_load_dld_defaults_to_ready_and_offplan(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(transaction_number="READY-1"),
            make_row(
                transaction_number="OFFPLAN-1",
                is_offplan="Off-Plan",
            ),
        ],
    )

    sales = load_dld(path)

    assert len(sales) == 2
    assert "OFFPLAN" not in sales[0].quality_flags
    assert "OFFPLAN" in sales[1].quality_flags


def test_load_dld_ready_mode_excludes_offplan(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(transaction_number="READY-1"),
            make_row(
                transaction_number="OFFPLAN-1",
                is_offplan="Off-Plan",
            ),
        ],
    )

    sales = load_dld(path, readiness="ready")

    assert [sale.source_id for sale in sales] == ["DLD-READY-1"]
    assert all("OFFPLAN" not in sale.quality_flags for sale in sales)


def test_load_dld_offplan_mode_only_includes_offplan(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(transaction_number="READY-1"),
            make_row(
                transaction_number="OFFPLAN-1",
                is_offplan="Off-Plan",
            ),
        ],
    )

    sales = load_dld(path, readiness="offplan")

    assert [sale.source_id for sale in sales] == ["DLD-OFFPLAN-1"]
    assert "OFFPLAN" in sales[0].quality_flags


def test_load_dld_excludes_non_sales_and_nonresidential(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(transaction_number="SALE-1"),
            make_row(
                transaction_number="MORTGAGE",
                transaction_group="Mortgage",
            ),
            make_row(
                transaction_number="LAND",
                property_type="Land",
            ),
            make_row(
                transaction_number="COMMERCIAL",
                usage="Commercial",
            ),
        ],
    )

    sales = load_dld(path)

    assert [sale.source_id for sale in sales] == ["DLD-SALE-1"]


def test_load_dld_skips_invalid_price_or_area(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(transaction_number="VALID"),
            make_row(
                transaction_number="BAD-PRICE",
                transaction_value_aed="0",
            ),
            make_row(
                transaction_number="BAD-AREA",
                area_used_sqft="-10",
            ),
        ],
    )

    sales = load_dld(path)

    assert [sale.source_id for sale in sales] == ["DLD-VALID"]


def test_load_dld_skips_unknown_readiness(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(transaction_number="READY"),
            make_row(
                transaction_number="UNKNOWN",
                is_offplan="",
            ),
        ],
    )

    sales = load_dld(path)

    assert [sale.source_id for sale in sales] == ["DLD-READY"]


def test_load_dld_rejects_invalid_readiness(tmp_path):
    path = write_dld_csv(tmp_path, [make_row()])

    with pytest.raises(ValueError, match="readiness"):
        load_dld(path, readiness="completed")


def test_load_dld_includes_flats_only_for_apartment_benchmarks(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(
                transaction_number="FLAT",
                property_sub_type="Flat",
            ),
            make_row(
                transaction_number="OFFICE",
                property_sub_type="Office",
            ),
            make_row(
                transaction_number="HOTEL",
                property_sub_type="Hotel Apartment",
            ),
            make_row(
                transaction_number="SHOP",
                property_sub_type="Shop",
            ),
        ],
    )

    sales = load_dld(path)

    assert [sale.source_id for sale in sales] == ["DLD-FLAT"]


def test_load_dld_normalizes_room_layouts(tmp_path):
    path = write_dld_csv(
        tmp_path,
        [
            make_row(
                transaction_number="STUDIO",
                rooms="Studio",
            ),
            make_row(
                transaction_number="ONE-BED",
                rooms="1 B/R",
            ),
            make_row(
                transaction_number="TWO-BED",
                rooms="2 B/R",
            ),
            make_row(
                transaction_number="UNKNOWN",
                rooms="NA",
            ),
        ],
    )

    sales = load_dld(path)
    layouts = {sale.source_id: sale.layout for sale in sales}

    assert layouts["DLD-STUDIO"] == "studio"
    assert layouts["DLD-ONE-BED"] == "1 bedroom"
    assert layouts["DLD-TWO-BED"] == "2 bedroom"
    assert layouts["DLD-UNKNOWN"] == ""
