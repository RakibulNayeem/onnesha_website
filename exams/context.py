"""Numbers for the top-right bar: streak, points and notifications (derived, nothing stored)."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from . import roles
from .models import ExamQuestion, Question

POINTS_PER_CORRECT = 10


def _streak(user):
    """Consecutive days (ending today or yesterday) with at least one finished test."""
    days = {timezone.localtime(t).date() for t in
            user.exams.filter(submitted_at__isnull=False).values_list("submitted_at", flat=True)[:400]}
    day = timezone.localdate()
    if day not in days:
        day -= timedelta(days=1)
    n = 0
    while day in days:
        n, day = n + 1, day - timedelta(days=1)
    return n


def hud(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    points = ExamQuestion.objects.filter(
        exam__user=user, exam__submitted_at__isnull=False, is_correct=True).count() * POINTS_PER_CORRECT
    # Reminders stay until the thing they point at is done (finish the test, clear the queue).
    notes = [{"text": f"অসমাপ্ত পরীক্ষা: {e.title}", "url": reverse("exam_take", args=[e.pk]), "icon": "stopwatch"}
             for e in user.exams.filter(submitted_at__isnull=True)[:3]]
    if roles.can_approve(user):
        n = Question.objects.filter(status=Question.DRAFT).count()
        if n:
            notes.append({"text": f"{n}টি প্রশ্ন রিভিউয়ের অপেক্ষায়", "icon": "clipboard-check",
                          "url": "/django-admin/exams/question/?status__exact=draft"})
    return {"hud": {"points": points, "streak": _streak(user), "notes": notes}}
