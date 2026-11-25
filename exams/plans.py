"""Free vs Premium. One place decides who is Premium and what Free is limited to."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

PRICE = 199                 # taka, for one year
DAYS = 365
FREE_EXAMS_PER_MONTH = 3


def active_subscription(user):
    if not user.is_authenticated:
        return None
    return user.subscriptions.filter(status="active", ends_at__gt=timezone.now()).order_by("-ends_at").first()


def is_premium(user):
    """Staff never hit the limits, so they can test every part of the site."""
    return bool(user.is_authenticated and (user.is_staff or active_subscription(user)))


def exams_left(user):
    """Timed exams a Free student can still start this month (None = unlimited)."""
    if is_premium(user):
        return None
    start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return max(0, FREE_EXAMS_PER_MONTH - user.exams.filter(created__gte=start).count())


def approve(sub):
    """Start (or extend, when already Premium) the year for a paid subscription."""
    now = timezone.now()
    current = active_subscription(sub.user)
    begin = current.ends_at if current and current.pk != sub.pk else now
    sub.status, sub.starts_at, sub.ends_at = "active", begin, begin + timedelta(days=DAYS)
    sub.save(update_fields=["status", "starts_at", "ends_at"])


def pay_number():
    return getattr(settings, "PAYMENT_NUMBER", "")
