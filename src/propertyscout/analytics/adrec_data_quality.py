
import csv
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "adrec_sales_normalized.csv"
)

SQM_TO_SQFT = 10.7639104167


def number(value):
    try:
        result = float(value)
        return result if result > 0 else None
    except (TypeError, ValueError):
        return None


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None

    # Support common date formats without assuming one source format.
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def main():
    total = 0
    dates = []
    unparsed_dates = 0
    types = Counter()
    application_types = Counter()
    districts = Counter()
    communities = Counter()
    missing = Counter()
    valid_rates = []
    rate_comparisons = []
    share_values = Counter()

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            total += 1

            date = parse_date(row.get("sale_application_date"))
            if date:
                dates.append(date)
            elif (row.get("sale_application_date") or "").strip():
                unparsed_dates += 1

            types[(row.get("property_type") or "").strip() or "Unknown"] += 1
            application_types[
                (row.get("sale_application_type") or "").strip() or "Unknown"
            ] += 1
            districts[(row.get("district") or "").strip() or "Unknown"] += 1
            communities[(row.get("community") or "").strip() or "Unknown"] += 1

            price = number(row.get("property_sale_price_aed"))
            area = number(row.get("property_sold_area_sqm"))
            source_rate = number(row.get("source_rate_aed_per_sqm"))
            share = (row.get("property_sold_share") or "").strip()

            share_values[share or "Blank"] += 1

            if price is None:
                missing["price"] += 1
            if area is None:
                missing["sold area"] += 1
            if source_rate is None:
                missing["source rate"] += 1

            if price and area:
                calculated_rate = price / area
                valid_rates.append(calculated_rate)

                if source_rate:
                    ratio = calculated_rate / source_rate
                    rate_comparisons.append({
                        "calculated": calculated_rate,
                        "source": source_rate,
                        "ratio": ratio,
                    })

    print("=== ADREC Data Quality Report ===")
    print(f"Total rows: {total:,}")
    print(f"Distinct community labels: {len(communities) - ('Unknown' in communities):,}")
    print(f"Distinct district labels: {len(districts) - ('Unknown' in districts):,}")

    if dates:
        print(f"Parsed application date range: {min(dates).date()} to {max(dates).date()}")
    print(f"Nonblank dates that could not be parsed: {unparsed_dates:,}")

    print("\nMissing or invalid fields:")
    for field in ("price", "sold area", "source rate"):
        print(f"  {field:15} {missing[field]:>8,}")

    print("\nTop property types:")
    for name, count in types.most_common(12):
        print(f"  {name:35} {count:>8,}")

    print("\nSale application types:")
    for name, count in application_types.most_common():
        print(f"  {name:35} {count:>8,}")

    print("\nTop 15 districts:")
    for name, count in districts.most_common(15):
        print(f"  {name:35} {count:>8,}")

    print("\nTop 20 communities:")
    for name, count in communities.most_common(20):
        print(f"  {name:45} {count:>8,}")

    print("\nProperty sold share: most common raw values")
    for name, count in share_values.most_common(12):
        print(f"  {name:25} {count:>8,}")

    if rate_comparisons:
        ratios = [item["ratio"] for item in rate_comparisons]
        print("\nSource rate vs price / sold area:")
        print(f"Records with both rates: {len(ratios):,}")
        print(f"Median calculated/source rate ratio: {statistics.median(ratios):.4f}")
        print(
            "Within 5% of source rate: "
            f"{sum(0.95 <= ratio <= 1.05 for ratio in ratios):,} "
            f"({sum(0.95 <= ratio <= 1.05 for ratio in ratios) / len(ratios):.1%})"
        )
        print(
            "Ratio below 0.5 or above 2.0: "
            f"{sum(ratio < 0.5 or ratio > 2.0 for ratio in ratios):,}"
        )

    if valid_rates:
        print("\nBasic calculated rate statistics (AED/sqm):")
        print(f"Records with price and area: {len(valid_rates):,}")
        print(f"Median: {statistics.median(valid_rates):,.2f}")
        print(f"Converted median (AED/sqft): {statistics.median(valid_rates) / SQM_TO_SQFT:,.2f}")


if __name__ == "__main__":
    main()
