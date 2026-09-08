"""Small helpers shared by the views."""
from datetime import date, datetime
from decimal import Decimal

from .models import add_months, month_start


def parse_month(value, default=None):
    """Accept '2026-09' or '2026-09-01'; fall back to the current month."""
    if value:
        for fmt in ("%Y-%m", "%Y-%m-%d"):
            try:
                return month_start(datetime.strptime(value, fmt).date())
            except ValueError:
                continue
    return month_start(default or date.today())


def parse_month_range(params, start_key="from", end_key="to", fallback_key="month"):
    """Read a (start, end) month range off a query dict.

    Old links that carry a single `month=` still work — they land on a
    one-month range. Picking the months backwards fixes itself.
    """
    fallback = parse_month(params.get(fallback_key))
    start = parse_month(params.get(start_key), fallback)
    end = parse_month(params.get(end_key), fallback)
    if end < start:
        start, end = end, start
    return start, end


def month_options(centre_on=None, back=18, forward=6, include=()):
    """A list of (value, label) for the month dropdowns.

    `include` pins extra months into the list, so a bookmarked range that
    reaches outside the default window still shows both of its own picks.
    """
    centre_on = month_start(centre_on or date.today())
    first = add_months(centre_on, -back)
    last = add_months(centre_on, forward)
    for m in include:
        if m:
            m = month_start(m)
            first = min(first, m)
            last = max(last, m)

    out = []
    m = first
    while m <= last:
        out.append((m.strftime("%Y-%m"), m.strftime("%b %Y")))
        m = add_months(m, 1)
    return out


def months_between(start, end):
    """Every month start from `start` to `end`, both included."""
    out = []
    m = month_start(start)
    end = month_start(end)
    while m <= end:
        out.append(m)
        m = add_months(m, 1)
    return out


def range_label(start, end):
    """'September 2026' for one month, 'Sep 2026 – Dec 2026' for a range."""
    if start == end:
        return start.strftime("%B %Y")
    return f"{start:%b %Y} – {end:%b %Y}"


def range_context(params):
    """Everything the two month dropdowns and the page heading need."""
    start, end = parse_month_range(params)
    return {
        "start_month": start,
        "end_month": end,
        "end_exclusive": add_months(end, 1),
        "start_value": start.strftime("%Y-%m"),
        "end_value": end.strftime("%Y-%m"),
        "month_options": month_options(include=(start, end)),
        "range_label": range_label(start, end),
        "is_range": start != end,
        # Old templates and links still reach for a single month.
        "month": start,
        "month_value": start.strftime("%Y-%m"),
    }


def money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))
