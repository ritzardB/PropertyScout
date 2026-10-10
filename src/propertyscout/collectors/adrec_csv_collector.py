
import csv
import html
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "adrec_recent_sales.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "adrec_sales_normalized.csv"

SQM_TO_SQFT = 10.7639104167


def normalize_header(value: str) -> str:
    value = html.unescape(value).replace("*", "").strip()
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


HEADER_MAP = {
    "asset class": "asset_class",
    "property type": "property_type",
    "sale application date": "sale_application_date",
    "property sold area (sqm)": "property_sold_area_sqm",
    "land plot ground area (sqm)": "land_plot_ground_area_sqm",
    "property layout": "property_layout",
    "district": "district",
    "community": "community",
    "project name": "project_name",
    "property sale price (aed)": "property_sale_price_aed",
    "property sold share": "property_sold_share",
    "rate (aed per sqm)": "source_rate_aed_per_sqm",
    "sale application type": "sale_application_type",
    "sale sequence": "sale_sequence",
}


def clean(value):
    return (value or "").strip()


def parse_number(value):
    """Parse a numeric value without silently treating invalid data as zero."""
    value = clean(value).replace(",", "").replace("AED", "").strip()

    if not value:
        return None

    # Handle values represented in parentheses, such as (1200.50).
    negative = value.startswith("(") and value.endswith(")")
    if negative:
        value = value[1:-1].strip()

    try:
        result = float(value)
        return -result if negative else result
    except ValueError:
        return None


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"ADREC input file not found: {INPUT_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    missing_price = 0
    missing_area = 0
    missing_source_rate = 0
    header_counts = Counter()
    communities = set()
    property_types = Counter()
    application_types = Counter()

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as source:
        reader = csv.DictReader(source)

        if not reader.fieldnames:
            raise ValueError("The ADREC CSV has no header row.")

        # Decode HTML entities and normalize the source column names.
        original_headers = reader.fieldnames
        canonical_headers = {}

        for original in original_headers:
            decoded = normalize_header(original)
            canonical = HEADER_MAP.get(decoded)

            if canonical:
                canonical_headers[original] = canonical
                header_counts[canonical] += 1
            else:
                print(f"Unmapped source column: {original!r}")

        missing_columns = set(HEADER_MAP.values()) - set(
            canonical_headers.values()
        )
        if missing_columns:
            print("Warning: expected columns not found:")
            for name in sorted(missing_columns):
                print(f"  - {name}")

        fieldnames = [
            "asset_class",
            "property_type",
            "sale_application_date",
            "property_sold_area_sqm",
            "property_sold_area_sqft",
            "land_plot_ground_area_sqm",
            "land_plot_ground_area_sqft",
            "property_layout",
            "district",
            "community",
            "project_name",
            "property_sale_price_aed",
            "property_sold_share",
            "source_rate_aed_per_sqm",
            "source_rate_aed_per_sqft",
            "calculated_rate_aed_per_sqm",
            "calculated_rate_aed_per_sqft",
            "sale_application_type",
            "sale_sequence",
            "source",
        ]

        with OUTPUT_FILE.open(
            "w", newline="", encoding="utf-8-sig"
        ) as destination:
            writer = csv.DictWriter(destination, fieldnames=fieldnames)
            writer.writeheader()

            for source_row in reader:
                row = {
                    canonical_headers[key]: clean(value)
                    for key, value in source_row.items()
                    if key in canonical_headers
                }

                price = parse_number(row.get("property_sale_price_aed"))
                area_sqm = parse_number(
                    row.get("property_sold_area_sqm")
                )
                land_sqm = parse_number(
                    row.get("land_plot_ground_area_sqm")
                )
                source_rate = parse_number(
                    row.get("source_rate_aed_per_sqm")
                )

                # Retain every record, even if some numeric fields are absent.
                if price is None or price <= 0:
                    missing_price += 1
                if area_sqm is None or area_sqm <= 0:
                    missing_area += 1
                if source_rate is None or source_rate <= 0:
                    missing_source_rate += 1

                calculated_rate = (
                    price / area_sqm
                    if price is not None
                    and price > 0
                    and area_sqm is not None
                    and area_sqm > 0
                    else None
                )

                communities.add(clean(row.get("community")))
                property_types[clean(row.get("property_type")) or "Unknown"] += 1
                application_types[
                    clean(row.get("sale_application_type")) or "Unknown"
                ] += 1

                def rounded(value):
                    return round(value, 4) if value is not None else ""

                writer.writerow({
                    "asset_class": row.get("asset_class", ""),
                    "property_type": row.get("property_type", ""),
                    "sale_application_date": row.get(
                        "sale_application_date", ""
                    ),
                    "property_sold_area_sqm": rounded(area_sqm),
                    "property_sold_area_sqft": rounded(
                        area_sqm * SQM_TO_SQFT
                        if area_sqm is not None and area_sqm > 0
                        else None
                    ),
                    "land_plot_ground_area_sqm": rounded(land_sqm),
                    "land_plot_ground_area_sqft": rounded(
                        land_sqm * SQM_TO_SQFT
                        if land_sqm is not None and land_sqm > 0
                        else None
                    ),
                    "property_layout": row.get("property_layout", ""),
                    "district": row.get("district", ""),
                    "community": row.get("community", ""),
                    "project_name": row.get("project_name", ""),
                    "property_sale_price_aed": rounded(price),
                    "property_sold_share": row.get("property_sold_share", ""),
                    "source_rate_aed_per_sqm": rounded(source_rate),
                    "source_rate_aed_per_sqft": rounded(
                        source_rate / SQM_TO_SQFT
                        if source_rate is not None and source_rate > 0
                        else None
                    ),
                    "calculated_rate_aed_per_sqm": rounded(calculated_rate),
                    "calculated_rate_aed_per_sqft": rounded(
                        calculated_rate / SQM_TO_SQFT
                        if calculated_rate is not None
                        else None
                    ),
                    "sale_application_type": row.get(
                        "sale_application_type", ""
                    ),
                    "sale_sequence": row.get("sale_sequence", ""),
                    "source": "Abu Dhabi Real Estate Centre",
                })

                rows_written += 1

    print("\n=== ADREC CSV Import ===")
    print(f"Rows imported: {rows_written:,}")
    print(f"Missing/invalid sale price: {missing_price:,}")
    print(f"Missing/invalid sold area: {missing_area:,}")
    print(f"Missing/invalid source rate: {missing_source_rate:,}")
    print(f"Distinct community labels: {len(communities - {''}):,}")

    print("\nProperty types:")
    for name, count in property_types.most_common(15):
        print(f"  {name:30} {count:>8,}")

    print("\nSale application types:")
    for name, count in application_types.most_common(15):
        print(f"  {name:30} {count:>8,}")

    print(f"\nNormalized output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
