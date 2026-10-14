import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from propertyscout import api
from propertyscout.rentals import api as rentals_api
from propertyscout.rentals import csv_store

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def isolate_rental_csv(tmp_path, monkeypatch):
    test_file = tmp_path / "rental_listings.csv"
    monkeypatch.setattr(csv_store, "RENTAL_DATA_FILE", test_file)
    yield


def make_listing(**overrides):
    payload = {
        "title": "Apartment for rent",
        "emirate": "Abu Dhabi",
        "property_type": "Apartment",
        "community": "Al Reem Island",
        "annual_rent_aed": 80000,
        "source_name": "Authorized Test Feed",
        "source_url": "https://example.com/listings/123",
        "external_listing_id": "TEST-123",
    }
    payload.update(overrides)
    return payload


def test_rental_search_returns_empty_list_initially():
    response = client.get("/rentals")

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_retrieve_rental_listing():
    response = client.post("/rentals", json=make_listing())

    assert response.status_code == 201
    listing = response.json()
    assert listing["title"] == "Apartment for rent"
    assert listing["availability_status"] == "Advertised"
    assert listing["id"]

    detail = client.get(f"/rentals/{listing['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == listing["id"]


def test_search_filters_by_emirate_and_property_type():
    client.post("/rentals", json=make_listing())
    client.post(
        "/rentals",
        json=make_listing(
            title="Dubai warehouse",
            emirate="Dubai",
            property_type="Warehouse",
            community="Al Quoz",
            annual_rent_aed=150000,
            external_listing_id="TEST-456",
        ),
    )

    response = client.get(
        "/rentals",
        params={
            "emirate": "Abu Dhabi",
            "property_type": "Apartment",
            "community": "reem",
            "min_annual_rent": 50000,
            "max_annual_rent": 100000,
        },
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["community"] == "Al Reem Island"


def test_duplicate_source_listing_id_is_rejected():
    first = client.post("/rentals", json=make_listing())
    duplicate = client.post("/rentals", json=make_listing())

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_availability_can_be_updated():
    created = client.post("/rentals", json=make_listing()).json()

    response = client.patch(
        f"/rentals/{created['id']}/availability",
        params={"availability": "Confirmed Available"},
    )

    assert response.status_code == 200
    assert response.json()["availability_status"] == "Confirmed Available"
    assert response.json()["availability_checked_date"] is not None


def test_invalid_rent_range_is_rejected():
    response = client.get(
        "/rentals",
        params={
            "min_annual_rent": 100000,
            "max_annual_rent": 50000,
        },
    )

    assert response.status_code == 422


def test_update_rental_listing():
    created_response = client.post("/rentals", json=make_listing())
    assert created_response.status_code == 201
    created = created_response.json()

    response = client.patch(
        f"/rentals/{created['id']}",
        json={
            "title": "Updated apartment",
            "annual_rent_aed": 90000,
            "private_notes": "Contact owner directly",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated apartment"
    assert updated["annual_rent_aed"] == 90000
    assert updated["private_notes"] == "Contact owner directly"
    assert updated["community"] == "Al Reem Island"


def test_update_missing_rental_returns_404():
    response = client.patch(
        "/rentals/nonexistent-listing-id",
        json={"title": "Updated apartment"},
    )
    assert response.status_code == 404


def test_create_personal_listing_without_source_url():
    payload = make_listing(
        source_name="Personal Collection",
        source_url=None,
        external_listing_id=None,
    )

    response = client.post("/rentals", json=payload)

    assert response.status_code == 201
    listing = response.json()
    assert listing["source_url"] is None
    assert listing["listing_origin"] == "Personal Collection"
