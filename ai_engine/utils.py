from __future__ import annotations

from datetime import date, timedelta


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator in (0, 0.0, None):
        return default
    return float(numerator) / float(denominator)


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def last_n_days(today: date, days: int) -> tuple[date, date]:
    start = today - timedelta(days=max(days - 1, 0))
    return start, today
