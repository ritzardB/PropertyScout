
import csv
import json
from pathlib import Path
from typing import Any

from propertyscout.comparables.matching import RankedComparable


def export_report_json(report: dict[str, Any], output_path: str | Path) -> Path:
    """Export the complete comparable report to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write("\n")

    return path


def export_report_csv(report: dict[str, Any], output_path: str | Path) -> Path:
    """Export the main benchmark and sensitivity figures as one CSV row."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    target = report.get("target", {})
    review = report.get("review", {})

    row = {
        "report_date": report.get("report_date"),
        "emirate": target.get("emirate"),
        "district": target.get("district"),
        "project": target.get("project"),
        "layout": target.get("layout"),
        "transaction_count": report.get("transaction_count"),
        "median_aed_per_sqft": report.get("median_aed_per_sqft"),
        "p25_aed_per_sqft": report.get("p25_aed_per_sqft"),
        "p75_aed_per_sqft": report.get("p75_aed_per_sqft"),
        "min_aed_per_sqft": report.get("min_aed_per_sqft"),
        "max_aed_per_sqft": report.get("max_aed_per_sqft"),
        "flagged_transaction_count": review.get("flagged_transaction_count"),
        "review_threshold_aed_per_sqft": (
            review.get("price_outlier_threshold_aed_per_sqft")
        ),
        "sensitivity_median_aed_per_sqft": (
            review.get("sensitivity_median_aed_per_sqft")
        ),
        "sensitivity_p25_aed_per_sqft": (
            review.get("sensitivity_p25_aed_per_sqft")
        ),
        "sensitivity_p75_aed_per_sqft": (
            review.get("sensitivity_p75_aed_per_sqft")
        ),
        "transaction_date_from": report.get("transaction_date_from"),
        "transaction_date_to": report.get("transaction_date_to"),
        "sources": "; ".join(report.get("sources", [])),
        "warnings": "; ".join(report.get("warnings", [])),
        "disclaimer": report.get("disclaimer"),
    }

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)

    return path


def export_transactions_csv(
    matches: list[RankedComparable],
    output_path: str | Path,
    *,
    flagged_source_ids: set[str] | None = None,
) -> Path:
    """Export matched sales, matching scores, and review status."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flagged_source_ids = flagged_source_ids or set()

    fieldnames = [
        "source_id",
        "source_name",
        "transaction_date",
        "emirate",
        "district",
        "community",
        "project_name",
        "property_type",
        "layout",
        "sale_price_aed",
        "area_sqft",
        "price_per_sqft",
        "match_score",
        "quality_flags",
        "price_review_flag",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for match in matches:
            sale = match.sale
            writer.writerow({
                "source_id": sale.source_id,
                "source_name": sale.source_name,
                "transaction_date": sale.transaction_date,
                "emirate": sale.emirate,
                "district": sale.district,
                "community": sale.community,
                "project_name": sale.project_name,
                "property_type": sale.property_type,
                "layout": sale.layout,
                "sale_price_aed": sale.sale_price_aed,
                "area_sqft": sale.area_sqft,
                "price_per_sqft": sale.price_per_sqft,
                "match_score": match.score,
                "quality_flags": "; ".join(sale.quality_flags),
                "price_review_flag": sale.source_id in flagged_source_ids,
            })

    return path
