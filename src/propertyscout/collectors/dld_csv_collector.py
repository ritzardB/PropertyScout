
import csv
import html
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_FILE = PROJECT_ROOT / "data" / "raw" / "dld_transactions.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "dld_transactions_normalized.csv"

SQM_TO_SQFT = 10.7639104167


def normalize_header(value: str) -> str:
    """Normalize DLD headers, including HTML-encoded characters."""
    value = html.unescape(value).strip().lstrip("*").strip()
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)
    return value.strip("_").upper()


def parse_number(value: str) -> float | None:
    """Convert a numeric value to float, or None if unavailable."""
    value = (value or "").strip().replace(",", "")

    if not value or value.lower() in {"null", "none", "n/a", "-"}:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def import_dld_transactions() -> int:
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"DLD CSV not found: {RAW_FILE}\n"
            "Save the downloaded file as data/raw/dld_transactions.csv."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0
    skipped = 0

    with RAW_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as source:
        reader = csv.DictReader(source)

        if not reader.fieldnames:
            raise ValueError("The DLD CSV has no header row.")

        # Resolve source headers to normalized names.
        header_map = {
            normalize_header(name): name
            for name in reader.fieldnames
            if name
        }

        required = ["INSTANCE_DATE", "AREA_EN", "TRANS_VALUE"]
        missing = [name for name in required if name not in header_map]

        if missing:
            raise ValueError(
                f"Missing required DLD columns: {missing}\n"
                f"Detected columns: {list(header_map.keys())}"
            )

        fields = [
            "transaction_number",
            "transaction_date",
            "transaction_group",
            "procedure",
            "is_offplan",
            "is_freehold",
            "usage",
            "area",
            "property_type",
            "property_sub_type",
            "transaction_value_aed",
            "procedure_area_sqm",
            "actual_area_sqm",
            "area_used_sqm",
            "area_used_sqft",
            "aed_per_sqft",
            "rooms",
            "parking",
            "nearest_metro",
            "nearest_mall",
            "nearest_landmark",
            "total_buyer",
            "total_seller",
            "master_project",
            "project",
            "source",
        ]

        with OUTPUT_FILE.open(
            "w", newline="", encoding="utf-8-sig"
        ) as destination:
            writer = csv.DictWriter(destination, fieldnames=fields)
            writer.writeheader()

            for row in reader:
                def get(column: str) -> str:
                    original = header_map.get(column)
                    return (row.get(original) or "").strip() if original else ""

                value = parse_number(get("TRANS_VALUE"))
                actual_area = parse_number(get("ACTUAL_AREA"))
                procedure_area = parse_number(get("PROCEDURE_AREA"))

                # Prefer actual area, then procedure area as a fallback.
                area_sqm = (
                    actual_area if actual_area and actual_area > 0
                    else procedure_area
                )

                if value is None or value <= 0 or area_sqm is None or area_sqm <= 0:
                    skipped += 1
                    continue

                area_sqft = area_sqm * SQM_TO_SQFT

                writer.writerow({
                    "transaction_number": get("TRANSACTION_NUMBER"),
                    "transaction_date": get("INSTANCE_DATE"),
                    "transaction_group": get("GROUP_EN"),
                    "procedure": get("PROCEDURE_EN"),
                    "is_offplan": get("IS_OFFPLAN_EN"),
                    "is_freehold": get("IS_FREE_HOLD_EN"),
                    "usage": get("USAGE_EN"),
                    "area": get("AREA_EN"),
                    "property_type": get("PROP_TYPE_EN"),
                    "property_sub_type": get("PROP_SB_TYPE_EN"),
                    "transaction_value_aed": round(value, 2),
                    "procedure_area_sqm": procedure_area,
                    "actual_area_sqm": actual_area,
                    "area_used_sqm": round(area_sqm, 2),
                    "area_used_sqft": round(area_sqft, 2),
                    "aed_per_sqft": round(value / area_sqft, 2),
                    "rooms": get("ROOMS_EN"),
                    "parking": get("PARKING"),
                    "nearest_metro": get("NEAREST_METRO_EN"),
                    "nearest_mall": get("NEAREST_MALL_EN"),
                    "nearest_landmark": get("NEAREST_LANDMARK_EN"),
                    "total_buyer": get("TOTAL_BUYER"),
                    "total_seller": get("TOTAL_SELLER"),
                    "master_project": get("MASTER_PROJECT_EN"),
                    "project": get("PROJECT_EN"),
                    "source": "Dubai Land Department",
                })
                imported += 1

    print(f"Imported: {imported} transactions")
    print(f"Skipped: {skipped} records with missing or invalid price/area")
    print(f"Output: {OUTPUT_FILE}")
    return imported


if __name__ == "__main__":
    import_dld_transactions()
