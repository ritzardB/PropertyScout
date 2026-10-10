from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

from propertyscout.comparables.loaders import load_adrec, load_dld
from propertyscout.comparables.matching import find_comparables
from propertyscout.comparables.models import ComparableCriteria, ComparableSale
from propertyscout.comparables.reporting import build_comparable_report


app = FastAPI(
    title="PropertyScout API",
    description="Property intelligence and market analytics for the UAE.",
    version="0.1.0",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"

DLD_DATASET = DATA_DIR / "dld_transactions_normalized.csv"
ADREC_DATASET = DATA_DIR / "adrec_sales_normalized.csv"


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Report whether the PropertyScout API process is running."""
    return {
        "status": "healthy",
        "service": "PropertyScout API",
    }


@lru_cache(maxsize=3)
def get_sales(
    emirate: str,
    readiness: str,
) -> tuple[ComparableSale, ...]:
    """Load a server-controlled dataset once per source/filter."""
    if emirate == "Dubai":
        path = DLD_DATASET
        loader = lambda: load_dld(path, readiness=readiness)
    else:
        path = ADREC_DATASET
        loader = lambda: load_adrec(path)

    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Required transaction dataset is unavailable for {emirate}.",
        )

    try:
        return tuple(loader())
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read the transaction dataset for {emirate}.",
        ) from exc


@app.get("/comparables", tags=["Property Analytics"])
def get_comparables(
    emirate: Literal["Dubai", "Abu Dhabi"],
    district: str = Query(min_length=1, max_length=150),
    project_name: str | None = Query(default=None, max_length=200),
    community: str | None = Query(default=None, max_length=200),
    layout: str | None = Query(default=None, max_length=50),
    area_sqft: float | None = Query(default=None, gt=0, le=1_000_000),
    transaction_date_from: str | None = None,
    transaction_date_to: str | None = None,
    recent_days: int | None = Query(default=None, gt=0, le=3650),
    readiness: Literal["all", "ready", "offplan"] = "all",
    limit: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=20, ge=0, le=100),
) -> dict:
    """Find and summarize historical comparable apartment sales."""
    if (
        transaction_date_from
        and transaction_date_to
        and transaction_date_from > transaction_date_to
    ):
        raise HTTPException(
            status_code=422,
            detail="transaction_date_from must not be after transaction_date_to.",
        )

    # Validate date strings before they reach the matching engine.
    from datetime import date

    try:
        if transaction_date_from:
            transaction_date_from = date.fromisoformat(
                transaction_date_from
            ).isoformat()
        if transaction_date_to:
            transaction_date_to = date.fromisoformat(
                transaction_date_to
            ).isoformat()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Transaction dates must use YYYY-MM-DD format.",
        ) from exc

    # Readiness only applies to the Dubai DLD dataset.
    effective_readiness = readiness if emirate == "Dubai" else "all"

    sales = get_sales(emirate, effective_readiness)

    criteria = ComparableCriteria(
        emirate=emirate,
        district=district.strip(),
        project_name=project_name.strip() if project_name else None,
        community=community.strip() if community else None,
        layout=layout.strip() if layout else None,
        area_sqft=area_sqft,
        transaction_date_from=transaction_date_from,
        transaction_date_to=transaction_date_to,
        recent_days=recent_days,
    )

    matches = find_comparables(
        list(sales),
        criteria,
        limit=limit,
        min_score=min_score,
    )

    report = build_comparable_report(
        matches,
        target_project=criteria.project_name or "",
        target_layout=criteria.layout or "",
        target_district=criteria.district,
        target_emirate=criteria.emirate,
    )

    transactions = [
        {
            **asdict(match.sale),
            "score": match.score,
            "match_reasons": match.reasons,
        }
        for match in matches
    ]

    return {
        "report": report,
        "results": transactions,
        "result_count": len(transactions),
        "filters": {
            "emirate": emirate,
            "district": criteria.district,
            "project_name": criteria.project_name,
            "community": criteria.community,
            "layout": criteria.layout,
            "area_sqft": criteria.area_sqft,
            "transaction_date_from": criteria.transaction_date_from,
            "transaction_date_to": criteria.transaction_date_to,
            "recent_days": criteria.recent_days,
            "readiness": effective_readiness,
            "limit": limit,
            "min_score": min_score,
        },
    }
