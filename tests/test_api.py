from fastapi.testclient import TestClient

from propertyscout import api
from propertyscout.comparables.models import ComparableSale


client = TestClient(api.app)


def sample_sale() -> ComparableSale:
    return ComparableSale(
        source_id="TEST-001",
        source_name="Test Dataset",
        emirate="Dubai",
        transaction_date="2026-08-15",
        district="Dubai Marina",
        community="Dubai Marina",
        project_name="Marina Tower",
        property_type="Apartment",
        layout="studio",
        sale_price_aed=800_000,
        area_sqft=500,
        price_per_sqft=1600,
        source_reference="TEST-REF-001",
    )


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_comparables_endpoint_returns_matching_sale(monkeypatch):
    monkeypatch.setattr(
        api,
        "get_sales",
        lambda emirate, readiness: (sample_sale(),),
    )

    response = client.get(
        "/comparables",
        params={
            "emirate": "Dubai",
            "district": "Dubai Marina",
            "project_name": "Marina Tower",
            "layout": "studio",
            "area_sqft": 500,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["result_count"] == 1
    assert body["results"][0]["source_id"] == "TEST-001"
    assert body["results"][0]["sale_price_aed"] == 800_000
    assert body["results"][0]["price_per_sqft"] == 1600
    assert body["filters"]["emirate"] == "Dubai"
    assert "report" in body


def test_comparables_endpoint_rejects_invalid_area():
    response = client.get(
        "/comparables",
        params={
            "emirate": "Dubai",
            "district": "Dubai Marina",
            "area_sqft": 0,
        },
    )

    assert response.status_code == 422


def test_comparables_endpoint_requires_valid_emirate():
    response = client.get(
        "/comparables",
        params={
            "emirate": "Sharjah",
            "district": "Test District",
        },
    )

    assert response.status_code == 422
