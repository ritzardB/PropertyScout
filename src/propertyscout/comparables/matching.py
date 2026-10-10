from dataclasses import dataclass
from datetime import date, timedelta

from propertyscout.comparables.models import (
    ComparableCriteria,
    ComparableSale,
)


def norm(value: str | None) -> str:
    return (value or "").strip().casefold()


@dataclass
class RankedComparable:
    sale: ComparableSale
    score: float
    reasons: list[str]


def find_comparables(
    sales: list[ComparableSale],
    target: ComparableCriteria,
    limit: int = 20,
    min_score: float = 20.0,
) -> list[RankedComparable]:
    """Filter and rank comparable sales without mixing emirates."""

    ranked: list[RankedComparable] = []

    cutoff_date = None

    if target.recent_days is not None:
        if target.recent_days <= 0:
            raise ValueError("recent_days must be a positive number")

        cutoff_date = (
            date.today() - timedelta(days=target.recent_days)
        ).isoformat()

    for sale in sales:
        if cutoff_date and sale.transaction_date < cutoff_date:
            continue

        if norm(sale.emirate) != norm(target.emirate):
            continue

        if (
            target.transaction_date_from
            and sale.transaction_date < target.transaction_date_from
        ):
            continue

        if (
            target.transaction_date_to
            and sale.transaction_date > target.transaction_date_to
        ):
            continue

        if norm(sale.property_type) != norm(target.property_type):
            continue

        # If a layout is specified, do not mix different layouts.
        if target.layout and norm(sale.layout) != norm(target.layout):
            continue

        score = 0.0
        reasons: list[str] = []

        if target.project_name and norm(sale.project_name) == norm(
            target.project_name
        ):
            score += 50
            reasons.append("Same project")
        elif target.community and norm(sale.community) == norm(
            target.community
        ):
            score += 30
            reasons.append("Same community")
        elif norm(sale.district) == norm(target.district):
            score += 20
            reasons.append("Same district")
        else:
            continue

        if target.layout:
            score += 25
            reasons.append("Same layout")

        if target.area_sqft and target.area_sqft > 0:
            ratio = sale.area_sqft / target.area_sqft

            if 0.80 <= ratio <= 1.20:
                score += 25
                reasons.append("Area within 20%")
            elif 0.65 <= ratio <= 1.35:
                score += 15
                reasons.append("Area within 35%")
            elif 0.50 <= ratio <= 1.50:
                score += 5
                reasons.append("Area within 50%")

        if score >= min_score:
            ranked.append(
                RankedComparable(
                    sale=sale,
                    score=score,
                    reasons=reasons,
                )
            )

    # Highest relevance first; newest transaction first for equal scores.
        # Newest transactions first when relevance scores are tied.
    ranked.sort(
        key=lambda item: item.sale.transaction_date,
        reverse=True,
    )
    ranked.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return ranked[:limit]
