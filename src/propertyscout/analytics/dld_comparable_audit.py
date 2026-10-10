
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


def clean(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def audit_comparables() -> None:
    # Count procedures for each property type, subtype and status.
    combinations = Counter()
    flat_procedures = Counter()
    residential_types = Counter()
    area_variants = Counter()
    total_sales = 0

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        for row in csv.DictReader(file):
            if clean(row.get("transaction_group")).casefold() != "sales":
                continue

            total_sales += 1

            property_type = clean(row.get("property_type")) or "Unknown"
            subtype = clean(row.get("property_sub_type")) or "Unknown"
            status = clean(row.get("is_offplan")) or "Unknown"
            usage = clean(row.get("usage")) or "Unknown"
            procedure = clean(row.get("procedure")) or "Unknown"
            area = clean(row.get("area"))

            combinations[
                (property_type, subtype, status, procedure)
            ] += 1

            if usage.casefold() == "residential":
                residential_types[(property_type, subtype, status)] += 1

            # First valuation segment: residential flats, ready only.
            if (
                property_type.casefold() == "unit"
                and subtype.casefold() == "flat"
                and status.casefold() == "ready"
                and usage.casefold() == "residential"
            ):
                flat_procedures[procedure] += 1

                if area:
                    area_variants[area.upper()] += 1

    print(f"\nTotal sales-group records: {total_sales:,}")

    print("\n=== Residential property segments ===")
    for (ptype, subtype, status), count in residential_types.most_common():
        print(f"{ptype:10} | {subtype:25} | {status:10} | {count:>7,}")

    print("\n=== Ready residential flats: procedure mix ===")
    if flat_procedures:
        for procedure, count in flat_procedures.most_common():
            print(f"{procedure:50} {count:>7,}")
    else:
        print("No matching records found.")

    print("\n=== Top 20 areas for ready residential flats ===")
    for area, count in area_variants.most_common(20):
        print(f"{area:45} {count:>7,}")

    print("\n=== Procedure breakdown: selected property segments ===")
    selected_segments = {
        ("Unit", "Flat", "Ready"),
        ("Unit", "Flat", "Off-Plan"),
        ("Building", "Villa", "Ready"),
        ("Building", "Villa", "Off-Plan"),
        ("Unit", "Office", "Ready"),
        ("Unit", "Office", "Off-Plan"),
    }

    for segment in sorted(selected_segments):
        ptype, subtype, status = segment
        print(f"\n--- {ptype} | {subtype} | {status} ---")

        found = False
        for (row_type, row_subtype, row_status, procedure), count in (
            combinations.most_common()
        ):
            if (row_type, row_subtype, row_status) == segment:
                print(f"{procedure:50} {count:>7,}")
                found = True

        if not found:
            print("No matching records.")

if __name__ == "__main__":
    audit_comparables()
