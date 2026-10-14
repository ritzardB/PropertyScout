"""Persistent rental listing API."""


"""Persistent rental listing API."""

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from propertyscout.rentals import csv_store, media_store
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


def _require_rental(listing_id: str) -> None:
    """Raise 404 if the requested rental listing does not exist."""
    with _lock:
        if not any(
            listing.id == listing_id
            for listing in csv_store.load_rentals()
        ):
            raise HTTPException(
                status_code=404,
                detail="Rental listing not found.",
            )


def _media_metadata_path(listing_id: str) -> Path:
    """Return the metadata file for a listing's media."""
    return media_store.listing_media_dir(listing_id) / "media.json"


def _read_media_metadata(listing_id: str) -> list[dict]:
    """Load media metadata, returning an empty list if none exists."""
    metadata_path = _media_metadata_path(listing_id)

    if not metadata_path.exists():
        return []

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read rental media metadata.",
        ) from exc

    if not isinstance(data, list):
        raise HTTPException(
            status_code=500,
            detail="Rental media metadata has an invalid format.",
        )

    return data


def _write_media_metadata(listing_id: str, items: list[dict]) -> None:
    """Write metadata atomically to avoid partial JSON files."""
    metadata_path = _media_metadata_path(listing_id)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=metadata_path.parent,
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(items, file, indent=2)

        os.replace(temporary_path, metadata_path)

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@router.post(
    "/rentals/{listing_id}/media",
    status_code=status.HTTP_201_CREATED,
)
async def upload_rental_media(
    listing_id: str,
    file: UploadFile = File(...),
) -> dict:
    """Upload a photo or video for an existing rental listing."""
    _require_rental(listing_id)

    with _lock:
        saved = await media_store.save_upload(listing_id, file)

        items = _read_media_metadata(listing_id)
        item = {
            "id": uuid4().hex,
            "filename": saved["filename"],
            "media_type": saved["media_type"],
            "content_type": saved["content_type"],
            "size_bytes": saved["size_bytes"],
            "url": f"/rentals/{listing_id}/media/{saved['filename']}",
            "is_cover": not any(x.get("is_cover", False) for x in items)
            and saved["media_type"] == "image",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        items.append(item)
        _write_media_metadata(listing_id, items)

    return item


@router.get("/rentals/{listing_id}/media")
def list_rental_media(listing_id: str) -> list[dict]:
    """List photos and videos attached to a rental listing."""
    _require_rental(listing_id)

    with _lock:
        return _read_media_metadata(listing_id)


@router.get("/rentals/{listing_id}/media/{filename}")
def get_rental_media(listing_id: str, filename: str) -> FileResponse:
    """Serve a previously uploaded media file."""
    _require_rental(listing_id)

    # Only serve files registered in this listing's metadata.
    with _lock:
        items = _read_media_metadata(listing_id)
        item = next(
            (x for x in items if x.get("filename") == filename),
            None,
        )

    if item is None:
        raise HTTPException(status_code=404, detail="Media file not found.")

    directory = media_store.listing_media_dir(listing_id)
    file_path = directory / filename

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found.")

    return FileResponse(
        path=file_path,
        media_type=item["content_type"],
        filename=filename,
    )


@router.patch("/rentals/{listing_id}/media/{filename}/cover")
def set_rental_cover_photo(listing_id: str, filename: str) -> dict:
    """Set an uploaded image as the rental listing's cover photo."""
    _require_rental(listing_id)

    with _lock:
        items = _read_media_metadata(listing_id)

        selected = next(
            (item for item in items if item.get("filename") == filename),
            None,
        )

        if selected is None:
            raise HTTPException(
                status_code=404,
                detail="Media file not found.",
            )

        if selected.get("media_type") != "image":
            raise HTTPException(
                status_code=422,
                detail="Only images can be selected as the cover photo.",
            )

        media_dir = media_store.listing_media_dir(listing_id)
        if not (media_dir / filename).is_file():
            raise HTTPException(
                status_code=404,
                detail="Media file not found.",
            )

        for item in items:
            item["is_cover"] = item.get("filename") == filename

        _write_media_metadata(listing_id, items)

        return {
            "message": "Cover photo updated.",
            "filename": filename,
            "is_cover": True,
        }
