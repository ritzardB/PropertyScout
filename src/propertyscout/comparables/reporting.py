from collections import Counter
from collections.abc import Iterable
from datetime import date

from propertyscout.comparables.benchmarking import summarize_prices
from propertyscout.comparables.matching import RankedComparable


def build_comparable_report(
    matches: Iterable[RankedComparable],
    *,
    target_project: str,
    target_layout: str,
    target_district: str,
    target_emirate: str,
) -> dict:
    """Build a comparable-sales report with transparent quality review.

    All matched transactions remain in the headline benchmark.
    Transactions priced below 50% of the matched median are flagged
    for review and excluded only from the optional sensitivity calculation.
    """

    items = list(matches)
    prices = [item.sale.price_per_sqft for item in items]
    summary = summarize_prices(prices)

    # Use the median of all matched sales as the initial reference.
    initial_median = summary["median"]
    review_threshold = (
        initial_median * 0.50
        if initial_median is not None
        else None
    )

    flagged_transactions = []
    retained_prices = []
    quality_flag_counts = Counter()

    for item in items:
        sale = item.sale
        quality_flags = list(sale.quality_flags)

        for flag in quality_flags:
            quality_flag_counts[flag] += 1

        price_outlier = (
            review_threshold is not None
            and sale.price_per_sqft < review_threshold
        )

        if price_outlier:
            flagged_transactions.append(
                {
                    "source_id": sale.source_id,
                    "source_name": sale.source_name,
                    "transaction_date": sale.transaction_date,
                    "project_name": sale.project_name,
                    "layout": sale.layout,
                    "sale_price_aed": sale.sale_price_aed,
                    "area_sqft": sale.area_sqft,
                    "price_per_sqft": sale.price_per_sqft,
                    "reason": (
                        "Price per square foot is below 50% "
                        "of the initial matched median."
                    ),
                    "quality_flags": quality_flags,
                }
            )
        else:
            retained_prices.append(sale.price_per_sqft)

    # Count exact project/layout matches for context.
    exact_project_count = sum(
        1
        for item in items
        if item.sale.project_name.strip().casefold()
        == target_project.strip().casefold()
    )

    exact_layout_count = sum(
        1
        for item in items
        if item.sale.layout.strip().casefold()
        == target_layout.strip().casefold()
    )

    source_names = sorted(
        {
            item.sale.source_name
            for item in items
            if item.sale.source_name
        }
    )

    dates = [
        item.sale.transaction_date
        for item in items
        if item.sale.transaction_date
    ]

    sensitivity_summary = summarize_prices(retained_prices)

    warnings = []

    if not items:
        warnings.append("No comparable transactions matched the criteria.")

    if len(items) < 5:
        warnings.append(
            "Fewer than five comparable sales; interpret the benchmark cautiously."
        )

    if flagged_transactions:
        warnings.append(
            f"{len(flagged_transactions)} transaction(s) flagged for price review. "
            "They remain included in the headline benchmark."
        )

    if (
        summary["min"] is not None
        and summary["max"] is not None
        and summary["min"] > 0
        and summary["max"] / summary["min"] >= 2
    ):
        warnings.append(
            "Wide price range: review individual transactions and possible outliers."
        )

    return {
        "report_date": date.today().isoformat(),
        "target": {
            "emirate": target_emirate,
            "district": target_district,
            "project": target_project,
            "layout": target_layout,
        },
        "transaction_count": summary["count"],
        "median_aed_per_sqft": summary["median"],
        "p25_aed_per_sqft": summary["p25"],
        "p75_aed_per_sqft": summary["p75"],
        "min_aed_per_sqft": summary["min"],
        "max_aed_per_sqft": summary["max"],
        "transaction_date_from": min(dates) if dates else None,
        "transaction_date_to": max(dates) if dates else None,
        "exact_project_match_count": exact_project_count,
        "exact_layout_match_count": exact_layout_count,
        "sources": source_names,
        "quality_flag_counts": dict(sorted(quality_flag_counts.items())),
        "review": {
            "price_outlier_rule": (
                "Flag prices below 50% of the initial matched median."
            ),
            "price_outlier_threshold_aed_per_sqft": (
                round(review_threshold, 2)
                if review_threshold is not None
                else None
            ),
            "flagged_transaction_count": len(flagged_transactions),
            "flagged_transactions": flagged_transactions,
            "sensitivity_excluded_count": len(flagged_transactions),
            "sensitivity_median_aed_per_sqft": (
                sensitivity_summary["median"]
            ),
            "sensitivity_p25_aed_per_sqft": sensitivity_summary["p25"],
            "sensitivity_p75_aed_per_sqft": sensitivity_summary["p75"],
            "sensitivity_min_aed_per_sqft": sensitivity_summary["min"],
            "sensitivity_max_aed_per_sqft": sensitivity_summary["max"],
            "note": (
                "Sensitivity figures exclude price-outlier flags for comparison "
                "only. They do not establish that a flagged transaction is invalid."
            ),
        },
        "warnings": warnings,
        "methodology": {
            "benchmark": "Median price per square foot of matched transactions.",
            "outlier_handling": "Flag for review; retain in headline benchmark.",
            "date_basis": (
                "Uses transaction dates supplied by the source dataset; "
                "these may represent application dates rather than final "
                "registration dates."
            ),
        },
        "disclaimer": (
            "Historical recorded transactions; not an asking-price feed, "
            "formal valuation, or guarantee of current market value."
        ),
    }
