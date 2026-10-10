
from propertyscout.collectors.sample_collector import (
    collect_properties,
)
from propertyscout.storage.csv_store import save_properties


def main() -> None:
    listings = collect_properties()

    print("\n=== PropertyScout | Property Intelligence ===\n")

    for listing in listings:
        print(
            f"{listing.area}: {listing.title} | "
            f"{listing.transaction_type.title()} | "
            f"{listing.price_label}: AED {listing.unit_price:,.0f} | "
            f"{listing.size_sqft:,.0f} sqft | "
            f"AED {listing.price_per_sqft:,.2f}/sqft"
        )

    save_properties(listings)
    print("\nPropertyScout sample run completed successfully.")


if __name__ == "__main__":
    main()
