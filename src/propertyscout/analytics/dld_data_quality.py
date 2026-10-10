import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dld_transactions_normalized.csv"
)


def inspect_data() -> None:
    dates = Counter()
    groups = Counter()
    procedures = Counter()
    offplan = Counter()
    areas = Counter()
    total = 0

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            total += 1

            date = row["transaction_date"].strip()
            dates[date] += 1
            groups[row["transaction_group"].strip() or "Unknown"] += 1
            procedures[row["procedure"].strip() or "Unknown"] += 1
            offplan[row["is_offplan"].strip() or "Unknown"] += 1
            areas[row["area"].strip() or "Unknown"] += 1

    print("\n=== PropertyScout | DLD Data Quality ===")
    print(f"Total records: {total:,}")

    print("\n--- First 10 distinct transaction dates ---")
    for date, count in sorted(dates.items())[:10]:
        print(f"{date:<25} {count:>7,}")

    print("\n--- Last 10 distinct transaction dates ---")
    for date, count in sorted(dates.items())[-10:]:
        print(f"{date:<25} {count:>7,}")

    print(f"\nDistinct dates: {len(dates):,}")
    print(f"Distinct areas: {len(areas):,}")

    for title, counter in [
        ("Transaction groups", groups),
        ("Procedures", procedures),
        ("Off-plan values", offplan),
    ]:
        print(f"\n--- {title} ---")
        for value, count in counter.most_common(15):
            print(f"{value:<35} {count:>7,}")


if __name__ == "__main__":
    inspect_data()
