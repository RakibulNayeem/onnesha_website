"""Numbers for the top-right bar: streak, points and notifications (derived, nothing stored)."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from . import roles
from . import friends as fr
from .activity import POINTS_PER_CORRECT, daily_points, streak
from .i18n import num, tr
from .models import ExamQuestion, Question


def lang(request):
    from django.utils import translation
    return {"LANG": (translation.get_language() or "bn")[:2]}


def hud(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    points = ExamQuestion.objects.filter(
        exam__user=user, exam__submitted_at__isnull=False, is_correct=True).count() * POINTS_PER_CORRECT
    # Reminders stay until the thing they point at is done (finish the test, clear the queue).
    notes = [{"text": f"{tr('অসমাপ্ত পরীক্ষা')}: {e.title}", "url": reverse("exam_take", args=[e.pk]), "icon": "stopwatch"}
             for e in user.exams.filter(submitted_at__isnull=True)[:3]]
    n_req = fr.incoming(user).count()
    if n_req:
        notes.append({"text": f"{num(n_req)}{tr('টি বন্ধুর অনুরোধ')}", "icon": "person-plus", "url": reverse("exam_friends")})
    if roles.can_manage_users(user):
        from .models import Subscription
        n_pay = Subscription.objects.filter(status="pending").count()
        if n_pay:
            notes.append({"text": f"{num(n_pay)}{tr('টি প্রিমিয়াম পেমেন্ট যাচাইয়ের অপেক্ষায়')}", "icon": "gem",
                          "url": reverse("panel_payments")})
    if roles.can_approve(user):
        n = Question.objects.filter(status=Question.DRAFT).count()
        if n:
            notes.append({"text": f"{num(n)}{tr('টি প্রশ্ন রিভিউয়ের অপেক্ষায়')}", "icon": "clipboard-check",
                          "url": reverse("panel_questions") + "?status=draft"})
    return {"hud": {"points": points, "streak": streak(daily_points(user)), "notes": notes}}
