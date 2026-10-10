
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dld_transactions_normalized.csv"
)


def generate_report() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    total = 0
    areas = Counter()
    property_types = Counter()
    monthly_transactions = Counter()
    prices_by_area = defaultdict(list)
    values_by_area = defaultdict(list)

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            total += 1

            area = row["area"].strip() or "Unknown"
            property_type = row["property_type"].strip() or "Unknown"
            date = row["transaction_date"].strip()
            amount = float(row["transaction_value_aed"])
            price_per_sqft = float(row["aed_per_sqft"])

            areas[area] += 1
            property_types[property_type] += 1

            # DLD date format can vary, so take YYYY-MM when available.
            if len(date) >= 7 and date[4] in "-/":
                monthly_transactions[date[:7]] += 1

            prices_by_area[area].append(price_per_sqft)
            values_by_area[area].append(amount)

    print("\n=== PropertyScout | Dubai Market Report ===")
    print(f"\nTotal usable transactions: {total:,}")

    print("\n--- Top 10 Areas by Transaction Count ---")
    for area, count in areas.most_common(10):
        print(f"{area:<35} {count:>7,}")

    print("\n--- Property Types ---")
    for property_type, count in property_types.most_common():
        print(f"{property_type:<35} {count:>7,}")

    print("\n--- Top Areas by Median AED/sqft ---")
    print("(Areas with at least 20 records; mixed transaction types may remain.)")

    eligible_areas = [
        (area, median(prices))
        for area, prices in prices_by_area.items()
        if len(prices) >= 20
    ]

    for area, price in sorted(
        eligible_areas, key=lambda item: item[1], reverse=True
    )[:10]:
        print(f"{area:<35} AED {price:>10,.2f}/sqft")

    print("\n--- Monthly Transaction Counts ---")
    for month, count in sorted(monthly_transactions.items())[-12:]:
        print(f"{month:<12} {count:>7,}")

    print("\nReport completed.")


if __name__ == "__main__":
    generate_report()
