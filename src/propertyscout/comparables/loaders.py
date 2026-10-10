import csv
from pathlib import Path

from propertyscout.comparables.models import ComparableSale


def number(row: dict, key: str) -> float:
    try:
        return float((row.get(key) or "").replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def text(row: dict, key: str, default: str = "") -> str:
    return (row.get(key) or default).strip()


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def load_adrec(path: str | Path) -> list[ComparableSale]:
    """Load eligible ready-apartment transactions from ADREC."""

    sales: list[ComparableSale] = []

    for index, row in enumerate(read_rows(path), start=2):
        if text(row, "benchmark_eligible", "yes").casefold() != "yes":
            continue

        price = number(row, "property_sale_price_aed")
        area = number(row, "property_sold_area_sqft")
        rate = number(row, "calculated_rate_aed_per_sqft")

        if price <= 0 or area <= 0 or rate <= 0:
            continue

        # Use the source's rate as the benchmark field, but flag
        # material discrepancies for later review.
        calculated = price / area
        flags: list[str] = []

        if abs(rate - calculated) / calculated > 0.05:
            flags.append("RATE_MISMATCH_OVER_5_PERCENT")

        if price < 1000:
            flags.append("LOW_PRICE_REVIEW")

        sales.append(
            ComparableSale(
                source_id=f"ADREC-{index}",
                source_name="ADREC",
                emirate="Abu Dhabi",
                transaction_date=text(row, "sale_application_date"),
                district=text(row, "district"),
                community=text(row, "community"),
                project_name=text(row, "project_name"),
                property_type="Apartment",
                layout=text(row, "property_layout"),
                sale_price_aed=price,
                area_sqft=area,
                price_per_sqft=rate,
                source_reference=text(row, "source"),
                quality_flags=flags,
            )
        )

    return sales


def load_dld(
    path: str | Path,
    readiness: str = "all",
) -> list[ComparableSale]:
    """Load residential unit sales from normalized Dubai DLD data.

    Args:
        path: Path to the normalized DLD CSV.
        readiness: "all", "ready", or "offplan".
            "all" preserves both categories and flags off-plan sales.
    """
    readiness = readiness.strip().casefold()

    if readiness not in {"all", "ready", "offplan"}:
        raise ValueError(
            "readiness must be 'all', 'ready', or 'offplan'"
        )

    sales: list[ComparableSale] = []

    for index, row in enumerate(read_rows(path), start=2):
        if text(row, "transaction_group").casefold() != "sales":
            continue

        if text(row, "property_type").casefold() != "unit":
            continue

        if text(row, "usage").casefold() != "residential":
            continue

        if text(row, "property_sub_type").casefold() != "flat":
            continue

        source_readiness = text(row, "is_offplan").casefold()

        if source_readiness not in {"ready", "off-plan"}:
            # Do not silently classify unknown or missing status.
            continue

        is_offplan = source_readiness == "off-plan"

        if readiness == "ready" and is_offplan:
            continue

        if readiness == "offplan" and not is_offplan:
            continue

        price = number(row, "transaction_value_aed")
        area = number(row, "area_used_sqft")

        if price <= 0 or area <= 0:
            continue

        flags: list[str] = []
        if is_offplan:
            flags.append("OFFPLAN")

        transaction_number = text(row, "transaction_number")
        source_id = (
            f"DLD-{transaction_number}"
            if transaction_number
            else f"DLD-ROW-{index}"
        )

        sales.append(
            ComparableSale(
                source_id=source_id,
                source_name="Dubai Land Department",
                emirate="Dubai",
                transaction_date=text(row, "transaction_date"),
                district=text(row, "area"),
                community=text(row, "area"),
                project_name=text(row, "project") or text(
                    row, "master_project"
                ),
                property_type="Apartment",
                layout=normalize_dld_layout(text(row, "rooms")),
                sale_price_aed=price,
                area_sqft=area,
                price_per_sqft=price / area,
                source_reference=text(row, "source"),
                quality_flags=flags,
            )
        )

    return sales

def normalize_dld_layout(value: str) -> str:
    """Normalize DLD room labels to PropertyScout layout names."""
    normalized = value.strip().casefold()

    layouts = {
        "studio": "studio",
        "1 b/r": "1 bedroom",
        "2 b/r": "2 bedroom",
        "3 b/r": "3 bedroom",
        "4 b/r": "4 bedroom",
        "5 b/r": "5 bedroom",
        "6 b/r": "6 bedroom",
        "penthouse": "penthouse",
    }

    return layouts.get(normalized, "")




