
import csv
import json

import pytest

from propertyscout.comparables.benchmarking import (
    percentile,
    summarize_prices,
)
from propertyscout.comparables.exports import (
    export_report_csv,
    export_report_json,
    export_transactions_csv,
)
from propertyscout.comparables.matching import find_comparables
from propertyscout.comparables.models import (
    ComparableCriteria,
    ComparableSale,
)
from propertyscout.comparables.reporting import build_comparable_report


def make_sale(
    source_id="TEST-001",
    *,
    date="2026-09-01",
    price=1_000_000,
    area=500,
    price_per_sqft=None,
    project="Vista 1",
    district="Al Maryah Island",
    layout="studio",
):
    return ComparableSale(
        source_id=source_id,
        source_name="TEST",
        emirate="Abu Dhabi",
        transaction_date=date,
        district=district,
        community=district,
        project_name=project,
        property_type="Apartment",
        layout=layout,
        sale_price_aed=price,
        area_sqft=area,
        price_per_sqft=(
            price_per_sqft
            if price_per_sqft is not None
            else price / area
        ),
    )


def make_criteria(**overrides):
    values = {
        "emirate": "Abu Dhabi",
        "district": "Al Maryah Island",
        "project_name": "Vista 1",
        "property_type": "Apartment",
        "layout": "studio",
        "area_sqft": 500,
        "recent_days": None,
    }
    values.update(overrides)
    return ComparableCriteria(**values)


def make_report(matches):
    return build_comparable_report(
        matches,
        target_project="Vista 1",
        target_layout="studio",
        target_district="Al Maryah Island",
        target_emirate="Abu Dhabi",
    )


def test_percentile_interpolates_values():
    assert percentile([1000, 2000, 3000, 4000, 5000], 25) == 2000
    assert percentile([1000, 2000, 3000, 4000, 5000], 50) == 3000
    assert percentile([1000, 2000, 3000, 4000, 5000], 75) == 4000


def test_percentile_rejects_invalid_input():
    with pytest.raises(ValueError):
        percentile([], 50)

    with pytest.raises(ValueError):
        percentile([1000, 2000], 101)


def test_summarize_prices_ignores_nonpositive_values():
    result = summarize_prices([1000, 2000, 0, -5, None])

    assert result["count"] == 2
    assert result["median"] == 1500
    assert result["min"] == 1000
    assert result["max"] == 2000


def test_summarize_prices_handles_empty_input():
    result = summarize_prices([])

    assert result["count"] == 0
    assert result["median"] is None


def test_matching_prefers_same_project_and_layout():
    sales = [
        make_sale("OTHER-PROJECT", project="Different Project"),
        make_sale("OTHER-LAYOUT", layout="1 bedroom"),
        make_sale("EXACT-MATCH", date="2026-09-10"),
    ]

    matches = find_comparables(
        sales,
        make_criteria(),
        limit=10,
    )

    assert matches
    assert matches[0].sale.source_id == "EXACT-MATCH"


def test_matching_filters_wrong_emirate():
    sale = make_sale("DUBAI-SALE")
    sale.emirate = "Dubai"

    matches = find_comparables(
        [sale],
        make_criteria(),
        limit=10,
    )

    assert matches == []


def test_matching_applies_transaction_date_window():
    sales = [
        make_sale("RECENT", date="2026-09-01"),
        make_sale("OLD", date="2025-01-01"),
    ]

    matches = find_comparables(
        sales,
        make_criteria(
            transaction_date_from="2026-01-01",
            transaction_date_to="2026-09-30",
        ),
        limit=10,
    )

    assert [item.sale.source_id for item in matches] == ["RECENT"]


def test_matching_rejects_nonpositive_recent_days():
    with pytest.raises(ValueError):
        find_comparables(
            [make_sale()],
            make_criteria(recent_days=0),
            limit=10,
        )


def test_report_flags_low_price_without_removing_it():
    sales = [
        make_sale("NORMAL-1", price_per_sqft=2000),
        make_sale("NORMAL-2", price_per_sqft=2100),
        make_sale("NORMAL-3", price_per_sqft=2200),
        make_sale("LOW-SALE", price=400_000, area=529.58,
                  price_per_sqft=755.31, date="2026-06-23"),
    ]

    matches = find_comparables(
        sales,
        make_criteria(),
        limit=10,
    )
    report = make_report(matches)

    assert report["transaction_count"] == 4
    assert report["review"]["flagged_transaction_count"] == 1
    assert report["review"]["flagged_transactions"][0]["source_id"] == "LOW-SALE"
    assert report["review"]["sensitivity_excluded_count"] == 1
    assert report["review"]["sensitivity_median_aed_per_sqft"] is not None


def test_report_handles_no_matches():
    report = make_report([])

    assert report["transaction_count"] == 0
    assert report["median_aed_per_sqft"] is None
    assert report["review"]["flagged_transaction_count"] == 0
    assert "No comparable transactions matched the criteria." in report["warnings"]


def test_json_export_preserves_report(tmp_path):
    report = make_report([
        find_comparables(
            [make_sale()],
            make_criteria(),
            limit=10,
        )[0]
    ])

    output = export_report_json(
        report,
        tmp_path / "benchmark.json",
    )

    loaded = json.loads(output.read_text(encoding="utf-8"))

    assert loaded["transaction_count"] == 1
    assert loaded["target"]["project"] == "Vista 1"
    assert "review" in loaded


def test_summary_csv_contains_one_benchmark_row(tmp_path):
    report = make_report([
        find_comparables(
            [make_sale()],
            make_criteria(),
            limit=10,
        )[0]
    ])

    output = export_report_csv(
        report,
        tmp_path / "benchmark.csv",
    )

    with output.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["project"] == "Vista 1"
    assert rows[0]["transaction_count"] == "1"


def test_transaction_csv_marks_flagged_source(tmp_path):
    matches = find_comparables(
        [make_sale("LOW-SALE", price_per_sqft=755.31)],
        make_criteria(),
        limit=10,
    )

    output = export_transactions_csv(
        matches,
        tmp_path / "transactions.csv",
        flagged_source_ids={"LOW-SALE"},
    )

    with output.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["source_id"] == "LOW-SALE"
    assert rows[0]["price_review_flag"] == "True"
