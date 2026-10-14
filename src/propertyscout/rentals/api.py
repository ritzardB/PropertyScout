"""Persistent rental listing API."""

from datetime import date
from threading import RLock
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from propertyscout.rentals import csv_store
from propertyscout.rentals.models import (
    AvailabilityStatus,
    RentalEmirate,
    RentalListing,
    RentalListingCreate,
    RentalListingUpdate,
    RentalPropertyType,
)

router = APIRouter(tags=["Rental Discovery"])
_lock = RLock()


@router.get("/rentals", response_model=list[RentalListing])
def search_rentals(
    emirate: RentalEmirate | None = None,
    property_type: RentalPropertyType | None = None,
    community: str | None = Query(default=None, min_length=1, max_length=150),
    min_annual_rent: float | None = Query(default=None, ge=0),
    max_annual_rent: float | None = Query(default=None, gt=0),
    availability: AvailabilityStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RentalListing]:
    if min_annual_rent is not None and max_annual_rent is not None:
        if min_annual_rent > max_annual_rent:
            raise HTTPException(
                status_code=422,
                detail="min_annual_rent must not exceed max_annual_rent.",
            )

    with _lock:
        results = csv_store.load_rentals()

    if emirate is not None:
        results = [x for x in results if x.emirate == emirate]
    if property_type is not None:
        results = [x for x in results if x.property_type == property_type]
    if community:
        needle = community.strip().casefold()
        results = [x for x in results if needle in x.community.casefold()]
    if min_annual_rent is not None:
        results = [x for x in results if x.annual_rent_aed >= min_annual_rent]
    if max_annual_rent is not None:
        results = [x for x in results if x.annual_rent_aed <= max_annual_rent]
    if availability is not None:
        results = [x for x in results if x.availability_status == availability]

    return results[:limit]


@router.post(
    "/rentals",
    response_model=RentalListing,
    status_code=status.HTTP_201_CREATED,
)
def create_rental(payload: RentalListingCreate) -> RentalListing:
    with _lock:
        listings = csv_store.load_rentals()

        if payload.external_listing_id and any(
            x.source_name.casefold() == payload.source_name.casefold()
            and x.external_listing_id == payload.external_listing_id
            for x in listings
        ):
            raise HTTPException(
                status_code=409,
                detail="This source listing ID is already registered.",
            )

        listing = RentalListing(id=str(uuid4()), **payload.model_dump())
        csv_store.save_rentals([*listings, listing])
        return listing


@router.get("/rentals/{listing_id}", response_model=RentalListing)
def get_rental(listing_id: str) -> RentalListing:
    with _lock:
        for listing in csv_store.load_rentals():
            if listing.id == listing_id:
                return listing
    raise HTTPException(status_code=404, detail="Rental listing not found.")


@router.patch(
    "/rentals/{listing_id}",
    response_model=RentalListing,
)
def update_rental(
    listing_id: str,
    payload: RentalListingUpdate,
) -> RentalListing:
    """Update selected fields of an existing rental listing."""
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to update.",
        )

    with _lock:
        listings = csv_store.load_rentals()

        for index, listing in enumerate(listings):
            if listing.id != listing_id:
                continue

            merged_data = listing.model_dump()
            merged_data.update(updates)

            # Validate the complete record after applying changes.
            try:
                updated = RentalListing.model_validate(merged_data)
            except Exception as exc:
                raise HTTPException(
                    status_code=422,
                    detail="The updated listing contains invalid data.",
                ) from exc

            if updated.external_listing_id and any(
                other.id != listing_id
                and other.source_name.casefold()
                == updated.source_name.casefold()
                and other.external_listing_id
                == updated.external_listing_id
                for other in listings
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This source listing ID is already registered.",
                )

            listings[index] = updated
            csv_store.save_rentals(listings)
            return updated

    raise HTTPException(
        status_code=404,
        detail="Rental listing not found.",
    )

@router.patch(
    "/rentals/{listing_id}/availability",
    response_model=RentalListing,
)
def update_rental_availability(
    listing_id: str,
    availability: AvailabilityStatus,
) -> RentalListing:
    with _lock:
        listings = csv_store.load_rentals()

        for index, listing in enumerate(listings):
            if listing.id == listing_id:
                updated = listing.model_copy(
                    update={
                        "availability_status": availability,
                        "availability_checked_date": date.today(),
                    }
                )
                listings[index] = updated
                csv_store.save_rentals(listings)
                return updated

    raise HTTPException(status_code=404, detail="Rental listing not found.")
