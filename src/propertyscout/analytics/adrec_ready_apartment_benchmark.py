import csv
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "adrec_sales_normalized.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "adrec_ready_apartment_sales.csv"

SQM_TO_SQFT = 10.7639104167
MIN_DISTRICT_SALES = 20

# Provisional anomaly flag for ready-apartment records, not an official
# ADREC rule. Flag these for review instead of silently discarding them.
LOW_PRICE_REVIEW_THRESHOLD_AED = 1000


def clean(value):
    return " ".join((value or "").strip().split())


def positive_number(value):
    try:
        number = float(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def parse_date(value):
    value = clean(value)
    if not value:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    # Determine the date window from all parseable source dates.
    all_dates = []

    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            parsed = parse_date(row.get("sale_application_date"))
            if parsed:
                all_dates.append(parsed)

    if not all_dates:
        raise ValueError("No parseable application dates found.")

    latest_date = max(all_dates)
    start_date = latest_date - timedelta(days=365)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exported_records = []
    benchmark_records = []
    rejected_invalid = 0
    flagged_low_price = 0

    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if clean(row.get("property_type")).casefold() != "apartment":
                continue

            if clean(row.get("sale_application_type")).casefold() != "ready":
                continue

            application_date = parse_date(row.get("sale_application_date"))
            if (
                application_date is None
                or application_date < start_date
                or application_date > latest_date
            ):
                continue

            price = positive_number(row.get("property_sale_price_aed"))
            area_sqm = positive_number(row.get("property_sold_area_sqm"))

            if price is None or area_sqm is None:
                rejected_invalid += 1
                continue

            area_sqft = area_sqm * SQM_TO_SQFT
            rate_sqm = price / area_sqm
            rate_sqft = price / area_sqft

            low_price_flag = price < LOW_PRICE_REVIEW_THRESHOLD_AED
            if low_price_flag:
                flagged_low_price += 1

            record = {
                "sale_application_date": application_date.isoformat(),
                "district": clean(row.get("district")),
                "community": clean(row.get("community")),
                "asset_class": clean(row.get("asset_class")),
                "property_type": clean(row.get("property_type")),
                "property_layout": clean(row.get("property_layout")),
                "project_name": clean(row.get("project_name")),
                "sale_application_type": clean(
                    row.get("sale_application_type")
                ),
                "property_sale_price_aed": round(price, 2),
                "property_sold_area_sqm": round(area_sqm, 4),
                "property_sold_area_sqft": round(area_sqft, 2),
                "property_sold_share": clean(row.get("property_sold_share")),
                "source_rate_aed_per_sqm": (
                    positive_number(row.get("source_rate_aed_per_sqm"))
                    or ""
                ),
                "calculated_rate_aed_per_sqm": round(rate_sqm, 4),
                "calculated_rate_aed_per_sqft": round(rate_sqft, 2),
                "price_review_flag": (
                    "LOW_PRICE_REVIEW" if low_price_flag else ""
                ),
                "benchmark_eligible": "no" if low_price_flag else "yes",
            }

            # Export valid-area/price rows, including flagged rows, for audit.
            exported_records.append(record)

            # Only eligible rows contribute to the market statistics.
            if not low_price_flag:
                benchmark_records.append(record)

    if not exported_records:
        print("No qualifying ready-apartment records found.")
        print(f"Date range checked: {start_date} to {latest_date}")
        return

    fieldnames = list(exported_records[0].keys())
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(exported_records)

    districts = defaultdict(list)
    communities = defaultdict(list)

    for record in benchmark_records:
        rate = record["calculated_rate_aed_per_sqft"]
        if record["district"]:
            districts[record["district"]].append(rate)
        if record["community"]:
            communities[record["community"]].append(rate)

    print("=== ADREC Ready Apartment Benchmark ===")
    print(f"Date range: {start_date} to {latest_date}")
    print(f"Exported records with valid price/area: {len(exported_records):,}")
    print(f"Excluded for invalid price/area: {rejected_invalid:,}")
    print(f"Flagged for low-price review: {flagged_low_price:,}")
    print(f"Records used in market statistics: {len(benchmark_records):,}")
    print(f"Districts represented: {len(districts):,}")
    print(f"Communities represented: {len(communities):,}")
    print(f"Export: {OUTPUT_FILE}")

    print("\n=== Districts by median AED/sqft ===")
    print(f"(Minimum {MIN_DISTRICT_SALES} eligible records per district)")

    results = []
    for district, rates in districts.items():
        if len(rates) < MIN_DISTRICT_SALES:
            continue

        quartiles = statistics.quantiles(rates, n=4, method="inclusive")
        results.append({
            "district": district,
            "count": len(rates),
            "median": statistics.median(rates),
            "p25": quartiles[0],
            "p75": quartiles[2],
        })

    results.sort(key=lambda item: item["median"], reverse=True)

    print(
        f'{"District":35} {"Sales":>7} '
        f'{"Median":>12} {"P25":>12} {"P75":>12}'
    )
    for item in results:
        print(
            f'{item["district"][:35]:35} '
            f'{item["count"]:>7,} '
            f'{item["median"]:>12,.2f} '
            f'{item["p25"]:>12,.2f} '
            f'{item["p75"]:>12,.2f}'
        )


if __name__ == "__main__":
    main()
