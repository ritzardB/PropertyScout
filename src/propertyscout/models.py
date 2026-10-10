
from dataclasses import dataclass
from typing import Optional


@dataclass
class PropertyListing:
    listing_id: str
    title: str
    property_type: str
    transaction_type: str
    emirate: str
    area: str
    unit_price: float
    size_sqft: float
    source_name: str
    source_url: str

    # Use "once", "year", or "month"
    price_period: str = "once"

    bedrooms: Optional[int] = None
    project_status: Optional[str] = None

    def __post_init__(self) -> None:
        self.transaction_type = self.transaction_type.lower()
        self.price_period = self.price_period.lower()

        if self.transaction_type not in {"sale", "rent"}:
            raise ValueError(
                "transaction_type must be 'sale' or 'rent'."
            )

        if self.transaction_type == "sale":
            if self.price_period != "once":
                raise ValueError(
                    "Sale listings must use price_period='once'."
                )
        elif self.price_period not in {"year", "month"}:
            raise ValueError(
                "Rental listings must use price_period='year' "
                "or price_period='month'."
            )

        if self.unit_price < 0:
            raise ValueError("Price cannot be negative.")

        if self.size_sqft <= 0:
            raise ValueError("Property size must be greater than zero.")

    @property
    def price_per_sqft(self) -> float:
        """Return sale price or rental price per square foot."""
        return round(self.unit_price / self.size_sqft, 2)

    @property
    def price_label(self) -> str:
        """Describe the price and its payment period."""
        if self.transaction_type == "sale":
            return "Sale price"

        return f"Rent per {self.price_period}"


@dataclass
class ComparableCriteria:
    """Target-property details used to find comparable sales."""

    emirate: str
    district: str
    project_name: Optional[str] = None
    community: Optional[str] = None
    property_type: str = "Apartment"
    layout: Optional[str] = None
    area_sqft: Optional[float] = None
    transaction_date_from: Optional[str] = None
    transaction_date_to: Optional[str] = None
    recent_days: Optional[int] = None
