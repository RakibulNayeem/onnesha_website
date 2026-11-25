from django.contrib import messages
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
from .forms import ExamForm, ProfileForm
from .models import Chapter, Exam, ExamQuestion, Profile, Question, Source, Subject, Track

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


def _top_students(limit):
    since = timezone.now() - timezone.timedelta(days=30)
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

    letters = {}
    for x in by_kind("university"):          # Bangla alphabetical order, grouped by first letter
        letters.setdefault(x.name[:1], []).append(x)
    others = [(tr(label), by_kind(k)) for k, label in Source.KINDS[1:] if k != "board" and by_kind(k)]
    board_groups = {}                          # boards get their own tab, grouped by exam year (newest first)
    for x in by_kind("board"):
        board_groups.setdefault(x.year, []).append(x)
    return render(request, "exams/bank.html", {
        "tab": request.GET.get("tab") if request.GET.get("tab") in ("board", "institution") else "subject",
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
        pool = Question.objects.filter(status=Question.APPROVED, qtype=Question.MCQ).filter(
            _scope([x.pk for x in d["subjects"]], [c.pk for c in d["chapters"]]))
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
        "mode": "quick" if request.GET.get("mode") == "quick" else "mock"})


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
    graded = ExamQuestion.objects.filter(
        exam__user=request.user, exam__submitted_at__isnull=False)
    stats = dict(total=Count("id"), right=Count("id", filter=Q(is_correct=True)))
    subjects = _pct(graded.values(name=F("question__subject__name"))
                    .annotate(**stats).order_by("name"))
    chapters = _pct(graded.filter(question__chapter__isnull=False).values(
        name=F("question__chapter__name"),
        subject=F("question__subject__name"))
        .annotate(**stats))
    weak = sorted((c for c in chapters if c["total"] >= 3), key=lambda c: c["pct"])[:5]
    total = sum(x["total"] for x in subjects)
    return render(request, "exams/dashboard.html", {
        "n_exams": request.user.exams.filter(submitted_at__isnull=False).count(),
        "overall": round(100 * sum(x["right"] for x in subjects) / total) if total else 0,
        "exams": request.user.exams.filter(submitted_at__isnull=False)[:15],
        "open_exams": request.user.exams.filter(submitted_at__isnull=True)[:3],
        "subjects": subjects, "weak": weak})


def leaderboard(request):
    return render(request, "exams/leaderboard.html", {"rows": _top_students(20)})


def cq_practice(request):
    qs = Question.objects.filter(status=Question.APPROVED, qtype=Question.CQ, reserved=False).select_related(
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
            questions__qtype=Question.CQ, questions__status=Question.APPROVED, questions__reserved=False).distinct(),
        "chapters": Chapter.objects.filter(subject_id=subject) if subject else [],
        "sources": Source.objects.filter(
            questions__qtype=Question.CQ, questions__status=Question.APPROVED, questions__reserved=False).distinct(),
        "sel": {"subject": subject or "", "chapter": chapter or "", "source": source or ""}})


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
        "mine": Question.objects.filter(author=request.user).count() if request.user.is_staff else 0,
        "drafts": Question.objects.filter(status=Question.DRAFT).count() if roles.can_approve(request.user) else 0})



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
