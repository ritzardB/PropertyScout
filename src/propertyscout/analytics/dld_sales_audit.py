
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


def clean(value: str) -> str:
    return " ".join((value or "").strip().split())


def audit_sales() -> None:
    counts = Counter()
    area_names = Counter()
    total = 0

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            if clean(row["transaction_group"]).casefold() != "sales":
                continue

            total += 1

            property_type = clean(row["property_type"]) or "Unknown"
            subtype = clean(row["property_sub_type"]) or "Unknown"
            usage = clean(row["usage"]) or "Unknown"
            procedure = clean(row["procedure"]) or "Unknown"
            status = clean(row["is_offplan"]) or "Unknown"

            counts[("Property type", property_type)] += 1
            counts[("Usage", usage)] += 1
            counts[("Procedure", procedure)] += 1
            counts[("Property type + status", f"{property_type} | {status}")] += 1
            counts[("Type + subtype", f"{property_type} | {subtype}")] += 1

            area = clean(row["area"])
            if area:
                area_names[area.upper()] += 1

    print(f"\n=== DLD Sales Audit: {total:,} records ===")

    for category in (
        "Property type",
        "Usage",
        "Procedure",
        "Property type + status",
        "Type + subtype",
    ):
        print(f"\n--- {category} ---")
        matches = [
            (label, count)
            for (kind, label), count in counts.items()
            if kind == category
        ]
        for label, count in sorted(
            matches, key=lambda item: item[1], reverse=True
        )[:25]:
            print(f"{label:<55} {count:>7,}")

    print("\n--- Area labels that differ only by capitalization ---")
    for area, count in area_names.most_common(30):
        print(f"{area:<45} {count:>7,}")


if __name__ == "__main__":
    audit_sales()
