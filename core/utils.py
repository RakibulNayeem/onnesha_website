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


def month_options(centre_on=None, back=18, forward=6):
    """A list of (value, label) for the month dropdowns."""
    centre_on = month_start(centre_on or date.today())
    out = []
    for i in range(-back, forward + 1):
        m = add_months(centre_on, i)
        out.append((m.strftime("%Y-%m"), m.strftime("%b %Y")))
    return out


def money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))
