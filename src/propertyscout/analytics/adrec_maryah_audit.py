import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "data/processed/adrec_ready_apartment_sales.csv"
OUTPUT = ROOT / "data/processed/adrec_maryah_project_layout_audit.csv"

RATE = "calculated_rate_aed_per_sqft"
MIN_GROUP_SALES = 5

df = pd.read_csv(INPUT)

required = {
    "district",
    "project_name",
    "property_layout",
    "community",
    "property_sale_price_aed",
    "property_sold_area_sqft",
    RATE,
}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing required CSV columns: {sorted(missing)}")

# Use the same eligibility rule as the district benchmark.
if "benchmark_eligible" in df.columns:
    df = df[df["benchmark_eligible"].astype(str).str.casefold() == "yes"].copy()

maryah = df[
    df["district"].astype(str).str.strip().str.casefold()
    == "al maryah island"
].copy()

if maryah.empty:
    print("No eligible Al Maryah Island records found.")
    raise SystemExit(1)

maryah[RATE] = pd.to_numeric(maryah[RATE], errors="coerce")
maryah["property_sale_price_aed"] = pd.to_numeric(
    maryah["property_sale_price_aed"], errors="coerce"
)
maryah["property_sold_area_sqft"] = pd.to_numeric(
    maryah["property_sold_area_sqft"], errors="coerce"
)

maryah = maryah[
    maryah[RATE].notna()
    & (maryah[RATE] > 0)
    & maryah["property_sale_price_aed"].notna()
    & (maryah["property_sale_price_aed"] > 0)
    & maryah["property_sold_area_sqft"].notna()
    & (maryah["property_sold_area_sqft"] > 0)
].copy()

print("=== Al Maryah Island Project Audit ===")
print(f"Eligible records: {len(maryah):,}")
print(f"Rate field: {RATE}")
print(f"Minimum group size for detailed tables: {MIN_GROUP_SALES}")

def summarize(frame, group_columns):
    result = (
        frame.groupby(group_columns, dropna=False)
        .agg(
            sales=(RATE, "size"),
            median_aed_sqft=(RATE, "median"),
            p25_aed_sqft=(RATE, lambda s: s.quantile(0.25)),
            p75_aed_sqft=(RATE, lambda s: s.quantile(0.75)),
        )
        .reset_index()
    )
    return result.sort_values(
        ["median_aed_sqft", "sales"], ascending=[False, False]
    )

print("\n=== By Project ===")
project_summary = summarize(maryah, ["project_name"])
print(project_summary.round(2).to_string(index=False))

print("\n=== By Project and Layout ===")
layout_summary = summarize(
    maryah, ["project_name", "property_layout"]
)
print(
    layout_summary[layout_summary["sales"] >= MIN_GROUP_SALES]
    .round(2)
    .to_string(index=False)
)

print("\n=== By Community ===")
community_summary = summarize(maryah, ["community"])
print(community_summary.round(2).to_string(index=False))

print("\n=== Highest 15 Rates ===")
show = [
    "sale_application_date",
    "project_name",
    "property_layout",
    "community",
    "property_sale_price_aed",
    "property_sold_area_sqft",
    "property_sold_share",
    RATE,
]
show = [c for c in show if c in maryah.columns]
print(maryah.nlargest(15, RATE)[show].to_string(index=False))

# Export grouped project/layout benchmarks for reuse.
layout_summary.to_csv(OUTPUT, index=False)
print(f"\nProject/layout report exported: {OUTPUT}")
