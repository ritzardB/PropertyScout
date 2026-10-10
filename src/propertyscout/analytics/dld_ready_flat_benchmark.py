
import csv
import statistics
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dld_transactions_normalized.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "dld_ready_flat_sales.csv"

SQM_TO_SQFT = 10.7639104167
MIN_AREA_SALES = 10


def clean(value):
    return " ".join((value or "").strip().split())


def number(value):
    try:
        result = float(value)
        return result if result > 0 else None
    except (TypeError, ValueError):
        return None


def build_benchmark():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected = []
    excluded = 0

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if clean(row.get("transaction_group")).casefold() != "sales":
                continue
            if clean(row.get("property_type")).casefold() != "unit":
                continue
            if clean(row.get("property_sub_type")).casefold() != "flat":
                continue
            if clean(row.get("usage")).casefold() != "residential":
                continue
            if clean(row.get("is_offplan")).casefold() != "ready":
                continue
            if clean(row.get("procedure")).casefold() != "sale":
                continue

            price = number(row.get("transaction_value_aed"))
            area_sqm = number(row.get("area_used_sqm"))

            if price is None or area_sqm is None:
                excluded += 1
                continue

            area_sqft = area_sqm * SQM_TO_SQFT
            price_per_sqft = price / area_sqft

            if price_per_sqft <= 0:
                excluded += 1
                continue

            selected.append({
                "transaction_number": clean(
                    row.get("transaction_number")
                ),
                "transaction_date": clean(
                    row.get("transaction_date")
                ),
                "area": clean(row.get("area")).upper(),
                "property_type": clean(row.get("property_type")),
                "property_sub_type": clean(
                    row.get("property_sub_type")
                ),
                "usage": clean(row.get("usage")),
                "status": clean(row.get("is_offplan")),
                "procedure": clean(row.get("procedure")),
                "transaction_value_aed": round(price, 2),
                "area_sqm": round(area_sqm, 4),
                "area_sqft": round(area_sqft, 2),
                "aed_per_sqft": round(price_per_sqft, 2),
                "project": clean(row.get("project")),
                "master_project": clean(row.get("master_project")),
                "source": "Dubai Land Department",
            })

    if not selected:
        print("No qualifying records found.")
        return

    fieldnames = list(selected[0].keys())

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    prices_by_area = defaultdict(list)
    for row in selected:
        if row["area"]:
            prices_by_area[row["area"]].append(row["aed_per_sqft"])

    print("=== Ready Residential Flat Benchmark ===")
    print(f"Qualifying sales exported: {len(selected):,}")
    print(f"Excluded for invalid price/area: {excluded:,}")
    print(f"Unique areas: {len(prices_by_area):,}")
    print(f"Export: {OUTPUT_FILE}")

    print(
        "\n=== Areas ranked by median AED/sqft "
        f"(minimum {MIN_AREA_SALES} sales) ==="
    )

    summaries = []
    for area, prices in prices_by_area.items():
        if len(prices) < MIN_AREA_SALES:
            continue

        summaries.append({
            "area": area,
            "sales": len(prices),
            "median": statistics.median(prices),
        })

    summaries.sort(key=lambda item: item["median"], reverse=True)

    for item in summaries[:20]:
        print(
            f'{item["area"]:45} '
            f'Median AED/sqft: {item["median"]:>9,.2f} '
            f'({item["sales"]:,} sales)'
        )


if __name__ == "__main__":
    build_benchmark()
