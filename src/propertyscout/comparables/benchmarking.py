def percentile(values: list[float], percent: float) -> float:
    """Calculate a percentile using linear interpolation."""
    if not values:
        raise ValueError("Cannot calculate a percentile from an empty list.")

    if not 0 <= percent <= 100:
        raise ValueError("Percentile must be between 0 and 100.")

    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    result = ordered[lower] + (
        ordered[upper] - ordered[lower]
    ) * fraction

    return round(result, 2)


def summarize_prices(prices) -> dict:
    """Return descriptive statistics for positive price-per-square-foot values."""
    values = sorted(
        float(price)
        for price in prices
        if price is not None and float(price) > 0
    )

    if not values:
        return {
            "count": 0,
            "median": None,
            "p25": None,
            "p75": None,
            "min": None,
            "max": None,
        }

    middle = len(values) // 2
    if len(values) % 2:
        median = values[middle]
    else:
        median = (values[middle - 1] + values[middle]) / 2

    return {
        "count": len(values),
        "median": round(median, 2),
        "p25": percentile(values, 25),
        "p75": percentile(values, 75),
        "min": round(values[0], 2),
        "max": round(values[-1], 2),
    }
