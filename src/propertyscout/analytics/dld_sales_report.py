
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dld_transactions_normalized.csv"
)

MIN_RECORDS_PER_AREA = 10


def generate_sales_report() -> None:
    records = []
    skipped = 0

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            if row["transaction_group"].strip().casefold() != "sales":
                continue

            try:
                amount = float(row["transaction_value_aed"])
                price_per_sqft = float(row["aed_per_sqft"])
            except (TypeError, ValueError):
                skipped += 1
                continue

            if amount <= 0 or price_per_sqft <= 0:
                skipped += 1
                continue

            row["_amount"] = amount
            row["_price_per_sqft"] = price_per_sqft
            records.append(row)

    print("\n=== PropertyScout | DLD Sales Analysis ===")
    print(f"Sales-group records analyzed: {len(records):,}")
    print(f"Invalid records excluded: {skipped:,}")

    for status in ("Ready", "Off-Plan"):
        subset = [
            row for row in records
            if row["is_offplan"].strip().casefold() == status.casefold()
        ]

        by_area = defaultdict(list)

        for row in subset:
            area = row["area"].strip() or "Unknown"
            by_area[area].append(row["_price_per_sqft"])

        print(f"\n--- {status}: Top 15 Areas by Median AED/sqft ---")
        print(f"Records in category: {len(subset):,}")

        ranked = [
            (area, median(prices), len(prices))
            for area, prices in by_area.items()
            if area != "Unknown"
            and len(prices) >= MIN_RECORDS_PER_AREA
        ]

        for area, price, count in sorted(
            ranked, key=lambda item: item[1], reverse=True
        )[:15]:
            print(
                f"{area:<35} AED {price:>10,.2f}/sqft "
                f"({count:,} records)"
            )

    print("\nNote: Rankings mix property types and procedures.")
    print("Validate procedure and area definitions before valuation use.")


if __name__ == "__main__":
    generate_sales_report()
