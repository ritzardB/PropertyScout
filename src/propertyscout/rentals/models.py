"""Data models for PropertyScout rental listings."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RentalPropertyType(StrEnum):
    APARTMENT = "Apartment"
    VILLA = "Villa"
    COMMERCIAL = "Commercial"
    OFFICE = "Office"
    RETAIL_SHOP = "Retail shop"
    WAREHOUSE = "Warehouse"
    COMMERCIAL_BUILDING = "Commercial building"


class RentalEmirate(StrEnum):
    ABU_DHABI = "Abu Dhabi"
    DUBAI = "Dubai"


class AvailabilityStatus(StrEnum):
    ADVERTISED = "Advertised"
    UNVERIFIED = "Availability Unverified"
    CONFIRMED = "Confirmed Available"
    NO_LONGER_AVAILABLE = "No Longer Available"


class ListingOrigin(StrEnum):
    PERSONAL = "Personal Collection"
    FHI = "FHI"
    AUTHORIZED_FEED = "Authorized Feed"
    OTHER = "Other"


class RentalListingCreate(BaseModel):
    """Fields required to create a rental listing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=250)
    emirate: RentalEmirate
    property_type: RentalPropertyType
    community: str = Field(min_length=1, max_length=150)
    annual_rent_aed: float = Field(gt=0, le=1_000_000_000)

    bedrooms: int | None = Field(default=None, ge=0, le=100)
    area_sqft: float | None = Field(default=None, gt=0, le=10_000_000)

    description: str | None = Field(default=None, max_length=10_000)
    listing_origin: ListingOrigin = ListingOrigin.PERSONAL

    source_name: str = Field(
        default="Personal Collection",
        min_length=1,
        max_length=150,
    )
    source_url: HttpUrl | None = None
    external_listing_id: str | None = Field(default=None, max_length=200)

    advertised_date: date | None = None
    last_seen_date: date | None = None

    availability_status: AvailabilityStatus = AvailabilityStatus.ADVERTISED
    availability_checked_date: date | None = None

    contact_reference: str | None = Field(default=None, max_length=200)
    private_notes: str | None = Field(default=None, max_length=5000)


class RentalListingUpdate(BaseModel):
    """Fields that may be changed on an existing listing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=3, max_length=250)
    emirate: RentalEmirate | None = None
    property_type: RentalPropertyType | None = None
    community: str | None = Field(default=None, min_length=1, max_length=150)
    annual_rent_aed: float | None = Field(
        default=None, gt=0, le=1_000_000_000
    )

    bedrooms: int | None = Field(default=None, ge=0, le=100)
    area_sqft: float | None = Field(default=None, gt=0, le=10_000_000)

    description: str | None = Field(default=None, max_length=10_000)
    listing_origin: ListingOrigin | None = None
    source_name: str | None = Field(default=None, min_length=1, max_length=150)
    source_url: HttpUrl | None = None
    external_listing_id: str | None = Field(default=None, max_length=200)

    advertised_date: date | None = None
    last_seen_date: date | None = None
    availability_status: AvailabilityStatus | None = None
    availability_checked_date: date | None = None

    contact_reference: str | None = Field(default=None, max_length=200)
    private_notes: str | None = Field(default=None, max_length=5000)


class RentalListing(RentalListingCreate):
    """Stored rental listing with a PropertyScout identifier."""

    id: str = Field(min_length=1, max_length=100)
