"""Streaks and points, derived from finished exams (nothing extra is stored).

A day counts when the student finished at least one exam; each correct answer is worth POINTS_PER_CORRECT."""
from datetime import timedelta

from django.utils import timezone

POINTS_PER_CORRECT = 10
WEEK_START = 5            # the week runs Saturday to Friday; date.weekday() has Monday = 0


def daily_points(user):
    """{date: points} over the student's recent finished exams."""
    out = {}
    for t, correct in user.exams.filter(submitted_at__isnull=False).values_list("submitted_at", "correct")[:600]:
        d = timezone.localtime(t).date()
        out[d] = out.get(d, 0) + correct * POINTS_PER_CORRECT
    return out


def streak(days):
    """Consecutive active days ending today (or yesterday, so the streak survives until tonight)."""
    day = timezone.localdate()
    if day not in days:
        day -= timedelta(days=1)
    n = 0
    while day in days:
        n, day = n + 1, day - timedelta(days=1)
    return n


def week(days):
    """The seven days of this week (Sat..Fri) with whether each was active and its points."""
    today = timezone.localdate()
    start = today - timedelta(days=(today.weekday() - WEEK_START) % 7)
    return [{"date": d, "active": d in days, "points": days.get(d, 0), "today": d == today, "future": d > today}
            for d in (start + timedelta(days=i) for i in range(7))]


def summary(user):
    days = daily_points(user)
    w = week(days)
    return {"streak": streak(days), "week": w, "week_points": sum(x["points"] for x in w),
            "max_day": max([x["points"] for x in w] + [1])}


def month_grid(days, today=None):
    """This month as Saturday-first weeks of (date, in_month, active); drives the calendar card."""
    import calendar
    today = today or timezone.localdate()
    weeks = calendar.Calendar(firstweekday=WEEK_START).monthdatescalendar(today.year, today.month)
    return [[{"date": d, "in_month": d.month == today.month, "active": d in days, "today": d == today,
              "future": d > today} for d in w] for w in weeks]


BADGES = [  # (key, title, hint, test(stats))
    ("first", "প্রথম পরীক্ষা", "একটি পরীক্ষা শেষ করো", lambda s: s["exams"] >= 1),
    ("ten", "১০টি পরীক্ষা", "১০টি পরীক্ষা শেষ করো", lambda s: s["exams"] >= 10),
    ("s3", "৩ দিনের স্ট্রিক", "টানা ৩ দিন পরীক্ষা দাও", lambda s: s["best_streak"] >= 3),
    ("s7", "৭ দিনের স্ট্রিক", "টানা ৭ দিন পরীক্ষা দাও", lambda s: s["best_streak"] >= 7),
    ("c100", "১০০ সঠিক উত্তর", "মোট ১০০টি সঠিক উত্তর দাও", lambda s: s["correct"] >= 100),
    ("c500", "৫০০ সঠিক উত্তর", "মোট ৫০০টি সঠিক উত্তর দাও", lambda s: s["correct"] >= 500),
    ("sharp", "ধারালো মন", "কমপক্ষে ২০টি উত্তরে ৮০%+ সঠিকতা", lambda s: s["answered"] >= 20 and s["correct"] * 100 >= 80 * s["answered"]),
]


def best_streak(days):
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best, prev = max(best, run), d
    return best


def badges(stats):
    return [{"key": k, "title": t, "hint": h, "earned": bool(test(stats))} for k, t, h, test in BADGES]
