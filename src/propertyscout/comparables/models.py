from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ComparableSale:
    """A normalized recorded property transaction."""

    source_id: str
    source_name: str
    emirate: str
    transaction_date: str
    district: str
    community: str
    project_name: str
    property_type: str
    layout: str
    sale_price_aed: float
    area_sqft: float
    price_per_sqft: float
    source_reference: str = ""
    quality_flags: list[str] = field(default_factory=list)
    recent_days: Optional[int] = None

    def __post_init__(self) -> None:
        self.emirate = self.emirate.strip()
        self.district = self.district.strip()
        self.community = self.community.strip()
        self.project_name = self.project_name.strip()
        self.property_type = self.property_type.strip()
        self.layout = self.layout.strip()

        if self.sale_price_aed <= 0:
            raise ValueError("Sale price must be positive.")

        if self.area_sqft <= 0:
            raise ValueError("Area must be positive.")

        if self.price_per_sqft <= 0:
            raise ValueError("Price per sqft must be positive.")

    @property
    def calculated_price_per_sqft(self) -> float:
        return round(self.sale_price_aed / self.area_sqft, 2)


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
