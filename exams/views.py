from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import roles
from .i18n import tr
from . import activity, friends as fr, plans
from .forms import ExamForm, PaymentForm, ProfileForm
User = get_user_model()
from .models import Chapter, Exam, ExamQuestion, Friendship, PaymentProof, Profile, Question, Source, Subject, Subscription, Track

MCQ_OK = Q(questions__status=Question.APPROVED, questions__qtype=Question.MCQ, questions__reserved=False)


def _scope(subject_ids, chapter_ids):
    """Question filter for a mixed selection: a subject with ticked chapters is limited to
    those chapters; a subject with none ticked means the whole subject."""
    by = {}
    for c in Chapter.objects.filter(pk__in=chapter_ids):
        by.setdefault(c.subject_id, []).append(c.pk)
    cond = Q()
    for sid in subject_ids:
        cond |= Q(subject_id=sid, chapter_id__in=by[sid]) if sid in by else Q(subject_id=sid)
    return cond


def _top_students(limit, days=30):
    since = timezone.now() - timezone.timedelta(days=days)
    return (Exam.objects.filter(submitted_at__gte=since)
            .values("user__username").annotate(points=Sum("score"), exams=Count("id"))
            .order_by("-points")[:limit])


def home(request):
    mcq = Count("questions", filter=MCQ_OK)
    by_track = {}
    for subj in Subject.objects.annotate(mcq=mcq):
        by_track.setdefault(subj.track_id, []).append(subj)
    tracks = [(t, by_track.get(t.id, [])) for t in Track.objects.all()]
    sources = Source.objects.annotate(n=Count("questions", filter=Q(
        questions__status=Question.APPROVED))).filter(n__gt=0)
    return render(request, "exams/home.html", {
        "tracks": tracks, "sources": sources,
        "hero_q": Question.objects.filter(status=Question.APPROVED, qtype=Question.MCQ, reserved=False)
                  .select_related("subject").order_by("?").first(),
        "n_questions": Question.objects.filter(status=Question.APPROVED, reserved=False).count(),
        "n_subjects": Subject.objects.filter(MCQ_OK).distinct().count(),
        "n_banks": sources.count(),
        "n_tests": Exam.objects.filter(submitted_at__isnull=False).count(),
        "top": _top_students(5),
        # illustrative content for the "how it works" preview tabs
        "omr": [(i, i % 3 != 0) for i in range(1, 11)],
        "demo_lb": [(tr("তানভীর"), 128), (tr("নুসরাত"), 121), (tr("রাফি"), 117), (tr("মেহেরুন"), 109)]})


def quick_question(request):
    """One random approved MCQ as JSON, for the 'next question' button on the home card."""
    qs = Question.objects.filter(status=Question.APPROVED, qtype=Question.MCQ, reserved=False)
    if request.GET.get("exclude", "").isdigit():
        qs = qs.exclude(pk=request.GET["exclude"])
    q = qs.select_related("subject").order_by("?").first()
    if not q:
        return JsonResponse({"empty": True})
    return JsonResponse({
        "id": q.pk, "subject": q.subject.name, "text": q.text, "correct": q.correct,
        "explanation": q.explanation, "options": [{"k": k, "v": v} for k, v in q.options]})


def track_detail(request, slug):
    track = get_object_or_404(Track, slug=slug)
    subjects = track.subjects.annotate(mcq=Count("questions", filter=MCQ_OK))
    sources = Source.objects.filter(questions__subject__track=track,
                                    questions__status=Question.APPROVED, questions__reserved=False)\
        .annotate(n=Count("questions")).distinct()
    return render(request, "exams/track.html", {
        "track": track, "subjects": subjects, "sources": sources})


def bank(request):
    """Question bank: subject cards, or institutions (universities A-Z, then boards / jobs), with search."""
    approved = Q(questions__status=Question.APPROVED, questions__reserved=False)
    sources = list(Source.objects.annotate(n=Count("questions", filter=approved),
                                           held=Count("questions", filter=Q(questions__reserved=True)))
                   )
    sources = [x for x in sources if not (x.n == 0 and x.held)]   # model tests live only in exams

    def by_kind(kind):
        items = (x for x in sources if x.kind == kind)
        if kind == "board":                       # newest exam year first, then board name
            return sorted(items, key=lambda x: (-(x.year or 0), x.name))
        return sorted(items, key=lambda x: x.name)

    prof = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    tabs = prof.bank_tabs if prof else ("subject", "board", "institution")   # school levels have no institution tab
    tab = request.GET.get("tab") if request.GET.get("tab") in tabs else "subject"
    letters = {}
    for x in by_kind("university"):          # Bangla alphabetical order, grouped by first letter
        letters.setdefault(x.name[:1], []).append(x)
    others = [(tr(label), by_kind(k)) for k, label in Source.KINDS[1:] if k != "board" and by_kind(k)]
    board_groups = {}                          # boards get their own tab, grouped by exam year (newest first)
    for x in by_kind("board"):
        board_groups.setdefault(x.year, []).append(x)
    return render(request, "exams/bank.html", {
        "tab": tab, "tabs": tabs,
        "board_groups": list(board_groups.items()),
        "tracks": Track.objects.all(),
        "subjects": Subject.objects.select_related("track").annotate(
            n=Count("questions", filter=approved, distinct=True), chs=Count("chapters", distinct=True)),
        "uni_groups": list(letters.items()), "other_groups": others})


def subject_detail(request, pk):
    subject = get_object_or_404(Subject.objects.select_related("track"), pk=pk)
    chapters = subject.chapters.annotate(n=Count("questions", filter=Q(
        questions__status=Question.APPROVED, questions__qtype=Question.MCQ, questions__reserved=False)))
    total = subject.questions.filter(status=Question.APPROVED, qtype=Question.MCQ, reserved=False).count()
    sources = Source.objects.filter(questions__subject=subject, questions__status=Question.APPROVED,
                                    questions__reserved=False)\
        .annotate(n=Count("questions")).distinct()
    return render(request, "exams/subject.html", {
        "subject": subject, "chapters": chapters, "total": total, "sources": sources})


def practice(request):
    """Questions with instant answers. Without a selection, start at the subject list."""
    subject_ids = [int(x) for x in request.GET.getlist("subject") if x.isdigit()]
    chapter_ids = [int(x) for x in request.GET.getlist("chapter") if x.isdigit()]
    source_id = request.GET.get("source", "")
    if not (subject_ids or chapter_ids or source_id):
        return redirect(reverse("exam_build") + "?mode=quick")
    qs = Question.objects.filter(status=Question.APPROVED, qtype=Question.MCQ, reserved=False).select_related(
        "subject", "chapter", "source")
    if subject_ids:
        qs = qs.filter(_scope(subject_ids, chapter_ids))
    elif chapter_ids:
        qs = qs.filter(chapter_id__in=chapter_ids)
    if source_id.isdigit():
        qs = qs.filter(source_id=source_id)
    page = Paginator(qs.order_by("id"), 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    chips = [s.name for s in Subject.objects.filter(pk__in=subject_ids)]
    chips += [c.name for c in Chapter.objects.filter(pk__in=chapter_ids)]
    if source_id.isdigit():
        chips += [x.name for x in Source.objects.filter(pk=source_id)]
    return render(request, "exams/practice.html", {
        "page": page, "chips": chips, "qs": params.urlencode()})


def build(request):
    """Exam hub: pick topics, then start a timed model test or quick practice.
    Quick practice is open to everyone; creating a timed test needs an account."""
    if request.method == "POST" and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), "account_login")
    picked = request.POST.getlist("subjects") or request.GET.getlist("subject")
    form = ExamForm(request.POST or None, initial={"source": request.GET.get("source") or None})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        left = plans.exams_left(request.user)
        if left == 0:                                    # Free allowance used up
            messages.warning(request, tr("এই মাসের ফ্রি পরীক্ষা শেষ। আনলিমিটেড পরীক্ষার জন্য প্রিমিয়াম নাও।"))
            return redirect("exam_premium")
        pool = Question.objects.filter(status=Question.APPROVED, qtype=Question.MCQ).filter(
            _scope([x.pk for x in d["subjects"]], [c.pk for c in d["chapters"]]))
        if not plans.is_premium(request.user):          # held-back model-test questions are Premium only
            pool = pool.filter(reserved=False)
        if d["source"]:
            pool = pool.filter(source=d["source"])
        chosen = list(pool.order_by("?")[:d["count"]])
        if not chosen:
            form.add_error(None, "No approved questions match this selection yet.")
        else:
            if len(chosen) < d["count"]:
                messages.info(request, f"Only {len(chosen)} questions match - test shortened.")
            first = d["subjects"][0]
            exam = Exam.objects.create(
                user=request.user,
                title=", ".join(s.name for s in d["subjects"])[:200],
                duration_minutes=d["minutes"] or len(chosen),
                negative=0.25 if first.track.kind == "admission" else 0)
            ExamQuestion.objects.bulk_create(
                ExamQuestion(exam=exam, question=q, order=i) for i, q in enumerate(chosen, 1))
            return redirect("exam_take", pk=exam.pk)
    ok = Q(questions__status=Question.APPROVED, questions__qtype=Question.MCQ)
    subjects = [{"id": s.pk, "name": s.name, "track": s.track.name, "kind": s.track.kind, "n": s.n}
                for s in Subject.objects.filter(ok).select_related("track")
                .annotate(n=Count("questions", filter=ok, distinct=True)).distinct()]
    chapters = [{"id": c.pk, "name": c.name, "subject": c.subject_id, "n": c.n}
                for c in Chapter.objects.filter(subject__in=[s["id"] for s in subjects])
                .annotate(n=Count("questions", filter=Q(questions__status=Question.APPROVED,
                                                        questions__qtype=Question.MCQ)))]
    return render(request, "exams/build.html", {
        "form": form, "subjects": subjects, "chapters": chapters,
        "picked": [int(x) for x in picked if str(x).isdigit()],
        "picked_chapters": [int(x) for x in request.POST.getlist("chapters") if x.isdigit()],
        "picked_count": request.POST.get("count", "25"),
        "mode": "quick" if request.GET.get("mode") == "quick" else "mock",
        "exams_left": plans.exams_left(request.user) if request.user.is_authenticated else None})


@login_required(login_url="account_login")
def take(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    if exam.submitted_at:
        return redirect("exam_result", pk=pk)
    items = list(exam.items.select_related("question"))
    if request.method == "POST":
        answers = {i.question_id: request.POST.get(f"q{i.question_id}", "") for i in items}
        exam.submit({k: v for k, v in answers.items() if v in ("a", "b", "c", "d")})
        return redirect("exam_result", pk=pk)
    remaining = max(0, int((exam.deadline - timezone.now()).total_seconds()))
    return render(request, "exams/take.html", {
        "exam": exam, "items": items, "remaining": remaining})


@login_required(login_url="account_login")
def result(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    if not exam.submitted_at:
        return redirect("exam_take", pk=pk)
    items = list(exam.items.select_related("question", "question__chapter"))
    by_chapter = {}
    for i in items:
        name = i.question.chapter.name if i.question.chapter else "General"
        row = by_chapter.setdefault(name, [0, 0])
        row[1] += 1
        row[0] += i.is_correct is True
    return render(request, "exams/result.html", {
        "exam": exam, "items": items,
        "by_chapter": [(n, r, t, round(100 * r / t)) for n, (r, t) in by_chapter.items()]})


def _pct(rows):
    return [{**r, "pct": round(100 * r["right"] / r["total"])} for r in rows if r["total"]]


@login_required(login_url="account_login")
def dashboard(request):
    """Progress page: banner and stats, this week, month calendar, subject report, badges, recent exams."""
    me = request.user
    graded = ExamQuestion.objects.filter(exam__user=me, exam__submitted_at__isnull=False)
    stats = dict(total=Count("id"), right=Count("id", filter=Q(is_correct=True)))
    subjects = _pct(graded.values(name=F("question__subject__name")).annotate(**stats).order_by("name"))
    chapters = _pct(graded.filter(question__chapter__isnull=False).values(
        name=F("question__chapter__name"), subject=F("question__subject__name")).annotate(**stats))
    for sj in subjects:
        sj["chapters"] = sorted((c for c in chapters if c["subject"] == sj["name"]), key=lambda c: c["pct"])
    weak = sorted((c for c in chapters if c["total"] >= 3), key=lambda c: c["pct"])[:5]
    total = sum(x["total"] for x in subjects)
    right = sum(x["right"] for x in subjects)
    done = me.exams.filter(submitted_at__isnull=False)
    days = activity.daily_points(me)
    mine = done.aggregate(c=Sum("correct"))["c"] or 0
    rank = (Exam.objects.filter(submitted_at__isnull=False).values("user").annotate(c=Sum("correct"))
            .filter(c__gt=mine).count() + 1) if mine else None
    prof, _ = Profile.objects.get_or_create(user=me)
    batch = " ".join(x for x in (prof.get_level_display() if prof.level else "", str(prof.batch_year or "")) if x)
    act = activity.summary(me)
    return render(request, "exams/dashboard.html", {
        "n_exams": done.count(), "overall": round(100 * right / total) if total else 0,
        "exams": done[:8], "open_exams": me.exams.filter(submitted_at__isnull=True)[:3],
        "subjects": subjects, "weak": weak, "act": act, "batch": batch,
        "points": mine * activity.POINTS_PER_CORRECT, "rank": rank,
        "month": activity.month_grid(days), "month_label": timezone.localdate(),
        "badges": activity.badges({"exams": done.count(), "best_streak": activity.best_streak(days),
                                   "correct": right, "answered": total})})


def leaderboard(request):
    mine = []
    if request.user.is_authenticated:                      # you and your friends, this week
        group = [request.user, *fr.friends_of(request.user)]
        mine = sorted(({"user": u.username, "points": activity.summary(u)["week_points"], "me": u.pk == request.user.pk}
                       for u in group), key=lambda r: -r["points"])
    return render(request, "exams/leaderboard.html", {
        "week": _top_students(20, 7), "month": _top_students(20, 30), "friends_board": mine if len(mine) > 1 else []})


@login_required(login_url="account_login")
def public_profile(request, username):
    """A student's profile as friends see it: progress only. Contact details, birth date, address and school never appear."""
    who = get_object_or_404(User, username=username, is_active=True)
    link = fr.between(request.user, who) if who.pk != request.user.pk else None
    is_friend = who.pk == request.user.pk or bool(link and link.status == "accepted")
    prof = Profile.objects.filter(user=who).first()
    ctx = {"who": who, "is_friend": is_friend, "link": link, "is_me": who.pk == request.user.pk}
    if is_friend:
        ctx.update(p=activity.progress(who), month=activity.month_grid(activity.daily_points(who)),
                   month_label=timezone.localdate(),
                   batch=" ".join(x for x in (prof.get_level_display() if prof and prof.level else "",
                                              str(prof.batch_year) if prof and prof.batch_year else "") if x))
    return render(request, "exams/public_profile.html", ctx)


@login_required(login_url="account_login")
def friends(request):
    """Friends: search students, send/accept/decline requests, see each friend's streak and week."""
    me = request.user
    if request.method == "POST":
        do, other = request.POST.get("do"), User.objects.filter(pk=request.POST.get("user") or 0).first()
        if other and do == "send":
            msg = {"sent": "অনুরোধ পাঠানো হয়েছে।", "accepted": "তোমরা এখন বন্ধু!", "waiting": "অনুরোধ আগেই পাঠানো হয়েছে।",
                   "already": "তোমরা আগেই বন্ধু।", "self": "নিজেকে বন্ধু বানানো যায় না।"}[fr.send(me, other)]
            messages.info(request, tr(msg))
        elif other and do in ("accept", "decline"):
            link = Friendship.objects.filter(from_user=other, to_user=me, status="pending").first()
            if link and do == "accept":
                link.status = "accepted"
                link.save(update_fields=["status"])
            elif link:
                link.delete()
        elif other and do == "remove":
            link = fr.between(me, other)
            if link:
                link.delete()
        return redirect("exam_friends")
    q = request.GET.get("q", "").strip()
    found = []
    if len(q) >= 3:
        taken = {f.pk for f in fr.friends_of(me)}
        found = [{"u": u, "friend": u.pk in taken} for u in
                 User.objects.filter(username__icontains=q, is_active=True).exclude(pk=me.pk)[:8]]
    rows = []
    for f in fr.friends_of(me)[:50]:
        s = activity.summary(f)
        rows.append({"u": f, "streak": s["streak"], "week_points": s["week_points"], "today": any(d["active"] and d["today"] for d in s["week"])})
    return render(request, "exams/friends.html", {
        "q": q, "found": found, "rows": sorted(rows, key=lambda r: -r["week_points"]),
        "incoming": fr.incoming(me), "outgoing": fr.outgoing(me)})


def cq_practice(request):
    kinds = (Question.CQ, Question.SQ)       # creative and short questions share this page
    kind = request.GET.get("type") if request.GET.get("type") in kinds else ""
    qs = Question.objects.filter(status=Question.APPROVED, qtype__in=[kind] if kind else kinds, reserved=False).select_related(
        "subject", "chapter", "source")
    subject = request.GET.get("subject")
    chapter = request.GET.get("chapter")
    source = request.GET.get("source")
    if subject:
        qs = qs.filter(subject_id=subject)
    if chapter:
        qs = qs.filter(chapter_id=chapter)
    if source:
        qs = qs.filter(source_id=source)
    page = Paginator(qs.order_by("?" if request.GET.get("shuffle") else "-id"), 10)\
        .get_page(request.GET.get("page"))
    return render(request, "exams/cq.html", {
        "page": page, "subjects": Subject.objects.filter(
            questions__qtype__in=kinds, questions__status=Question.APPROVED, questions__reserved=False).distinct(),
        "chapters": Chapter.objects.filter(subject_id=subject) if subject else [],
        "sources": Source.objects.filter(
            questions__qtype__in=kinds, questions__status=Question.APPROVED, questions__reserved=False).distinct(),
        "sel": {"subject": subject or "", "chapter": chapter or "", "source": source or "", "type": kind}})


@login_required(login_url="account_login")
def profile(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=prof, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, tr("প্রোফাইল সংরক্ষণ করা হয়েছে।"))
        return redirect("exam_profile")
    done = request.user.exams.filter(submitted_at__isnull=False)
    totals = ExamQuestion.objects.filter(exam__in=done).aggregate(
        n=Count("id"), right=Count("id", filter=Q(is_correct=True)))
    return render(request, "exams/profile.html", {
        "form": form, "role": roles.label(request.user), "role_key": roles.role(request.user),
        "n_exams": done.count(), "accuracy": round(100 * totals["right"] / totals["n"]) if totals["n"] else 0,
        "can_panel": request.user.is_staff,
        "premium_until": getattr(plans.active_subscription(request.user), "ends_at", None),
        "is_premium": plans.is_premium(request.user), "exams_left": plans.exams_left(request.user) or 0,
        "mine": Question.objects.filter(author=request.user).count() if request.user.is_staff else 0,
        "drafts": Question.objects.filter(status=Question.DRAFT).count() if roles.can_approve(request.user) else 0})



@login_required(login_url="account_login")
def username_check(request):
    """Live availability hint for the profile's username field."""
    from django.contrib.auth.validators import UnicodeUsernameValidator
    from django.core.exceptions import ValidationError
    from .forms import username_taken
    name = request.GET.get("u", "").strip()
    try:
        if not name:
            raise ValidationError("empty")
        UnicodeUsernameValidator()(name)
    except ValidationError:
        return JsonResponse({"ok": False, "msg": tr("ইউজারনেম সঠিক নয়।")})
    if username_taken(name, request.user):
        return JsonResponse({"ok": False, "msg": tr("এই ইউজারনেম আগেই নেওয়া হয়েছে।")})
    return JsonResponse({"ok": True, "msg": tr("ইউজারনেমটি পাওয়া যাবে।")})


def premium(request):
    """Plans page: Free vs Premium, and the payment form (bKash / Nagad / Rocket + transaction id)."""
    user = request.user
    form = PaymentForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "account_login")
        if form.is_valid():
            sub = form.save(commit=False)
            sub.user, sub.amount = user, plans.PRICE
            sub.save()
            f = form.cleaned_data["proof"]
            PaymentProof.objects.create(subscription=sub, data=f.read(), content_type=f.detected_type,
                                        filename=f.name[:120])
            messages.success(request, tr("পেমেন্ট জমা হয়েছে। যাচাই শেষ হলেই প্রিমিয়াম চালু হবে।"))
            return redirect("exam_premium")
    mine = list(user.subscriptions.all()[:5]) if user.is_authenticated else []
    return render(request, "exams/premium.html", {
        "form": form, "price": plans.PRICE, "per_month": round(plans.PRICE / 12), "free_exams": plans.FREE_EXAMS_PER_MONTH,
        "active": plans.active_subscription(user), "pending": any(s.status == "pending" for s in mine),
        "mine": mine, "number": plans.pay_number()})


def set_language(request, code):
    """Remember the interface language, then go back to where the visitor was."""
    from django.utils.http import url_has_allowed_host_and_scheme
    back = request.META.get("HTTP_REFERER", "")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = reverse("exam_home")
    response = redirect(back)
    if code in ("bn", "en"):
        response.set_cookie("lang", code, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response
