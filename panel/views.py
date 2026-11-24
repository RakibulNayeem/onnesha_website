"""The staff panel (/panel/). Every view checks the role on the server; hiding a menu item is only cosmetic."""
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from exams import roles
from exams.models import Chapter, Exam, Question, Source, Subject, Track

from .forms import CONTENT, QuestionForm, UserForm, content_form

User = get_user_model()
ROLE_NAMES = {None: "Student", roles.TEACHER: "Teacher", roles.MODERATOR: "Moderator", roles.ADMIN: "Admin", "superuser": "Superuser"}


def panel_view(check=roles.can_use_panel):
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), "account_login")
            if not check(request.user):
                return render(request, "panel/forbidden.html", {"nav": nav(request)}, status=403)
            return view(request, *args, **kwargs)
        return wrapper
    return deco


def nav(request):
    u = request.user
    return {"can_approve": roles.can_approve(u), "can_content": roles.can_manage_content(u),
            "can_users": roles.can_manage_users(u), "role": ROLE_NAMES[roles.role(u)] if u.is_authenticated else "",
            "drafts": visible(u).filter(status=Question.DRAFT).count() if roles.can_use_panel(u) else 0}


def visible(user):
    """Questions this person may see: reviewers see all, teachers only their own."""
    qs = Question.objects.select_related("subject", "chapter", "source", "author")
    return qs if roles.can_approve(user) else qs.filter(author=user)


def page(request, qs, per=25):
    return Paginator(qs, per).get_page(request.GET.get("page"))


# ---------------------------------------------------------------- dashboard
@panel_view()
def dashboard(request):
    qs = visible(request.user)
    s = qs.aggregate(total=Count("id"), published=Count("id", filter=Q(status=Question.APPROVED)),
                     drafts=Count("id", filter=Q(status=Question.DRAFT)), mcq=Count("id", filter=Q(qtype=Question.MCQ)),
                     cq=Count("id", filter=Q(qtype=Question.CQ)))
    week = timezone.now() - timedelta(days=7)
    subjects = (Subject.objects.filter(questions__in=qs).annotate(n=Count("questions", distinct=True))
                .select_related("track").order_by("-n")[:8])
    top = max([x.n for x in subjects] or [1])
    ctx = {"nav": nav(request), "stats": s, "new_week": qs.filter(created__gte=week).count(),
           "subjects": [(x, round(100 * x.n / top)) for x in subjects],
           "queue": qs.filter(status=Question.DRAFT).order_by("-id")[:8], "section": "home"}
    if roles.can_manage_users(request.user):
        ctx["people"] = {"students": User.objects.filter(is_staff=False).count(), "staff": User.objects.filter(is_staff=True).count()}
        ctx["tests_week"] = Exam.objects.filter(submitted_at__gte=week).count()
    return render(request, "panel/dashboard.html", ctx)


# ---------------------------------------------------------------- questions
@panel_view()
def questions(request):
    user = request.user
    base = visible(user)
    if request.method == "POST":
        return _bulk(request, base)
    qs = base
    f = {k: request.GET.get(k, "") for k in ("q", "status", "type", "subject", "chapter", "source", "author")}
    if f["q"]:
        qs = qs.filter(Q(text__icontains=f["q"]) | Q(refs__icontains=f["q"]))
    if f["status"] in (Question.DRAFT, Question.APPROVED):
        qs = qs.filter(status=f["status"])
    if f["type"] in (Question.MCQ, Question.CQ):
        qs = qs.filter(qtype=f["type"])
    for key, col in (("subject", "subject_id"), ("chapter", "chapter_id"), ("source", "source_id"), ("author", "author_id")):
        if f[key].isdigit():
            qs = qs.filter(**{col: f[key]})
    params = request.GET.copy(); params.pop("page", None)
    ctx = {"nav": nav(request), "page": page(request, qs.order_by("-id")), "f": f, "qs": params.urlencode(), "section": "questions",
           "subjects": Subject.objects.select_related("track"), "chapters": Chapter.objects.filter(subject_id=f["subject"]) if f["subject"].isdigit() else [],
           "sources": Source.objects.all(), "authors": User.objects.filter(questions__isnull=False).distinct() if roles.can_approve(user) else []}
    return render(request, "panel/questions.html", ctx)


def _bulk(request, base):
    action = request.POST.get("bulk")
    if not roles.can_approve(request.user):
        return render(request, "panel/forbidden.html", {"nav": nav(request)}, status=403)
    picked = base.filter(pk__in=[int(x) for x in request.POST.getlist("ids") if x.isdigit()])
    if action == "approve":
        ok = [q for q in picked if not q.problems()]
        Question.objects.filter(pk__in=[q.pk for q in ok]).update(status=Question.APPROVED)
        messages.success(request, f"{len(ok)} published.")
        if len(ok) < picked.count():
            messages.warning(request, f"{picked.count() - len(ok)} skipped: missing options, answer or parts.")
    elif action == "draft":
        messages.success(request, f"{picked.update(status=Question.DRAFT)} sent back to draft.")
    elif action == "delete":
        done = blocked = 0
        for q in picked:
            try:
                q.delete(); done += 1
            except ProtectedError:
                blocked += 1
        messages.success(request, f"{done} deleted.")
        if blocked:
            messages.warning(request, f"{blocked} are used in student tests and cannot be deleted - send them back to draft instead.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("panel_questions"))


@panel_view()
def question_edit(request, pk=None):
    user = request.user
    obj = get_object_or_404(visible(user), pk=pk) if pk else None
    form = QuestionForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        q = form.save(commit=False)
        q.parts = form.parts
        creating = q.pk is None
        if creating:
            q.author = user
        action = request.POST.get("action", "save")
        if roles.can_approve(user):
            target = Question.APPROVED if action in ("approve", "approve_next") else Question.DRAFT if action == "draft" else (q.status or Question.DRAFT)
        else:
            target = Question.DRAFT            # teachers can never publish; editing sends a question back for review
        q.status = target
        if target == Question.APPROVED and q.problems():
            form.add_error(None, "Cannot publish yet: " + ", ".join(q.problems()) + ".")
        else:
            q.save()
            messages.success(request, "Published." if target == Question.APPROVED else "Saved as draft." if not roles.can_approve(user) else "Saved.")
            if action == "approve_next":
                nxt = visible(user).filter(status=Question.DRAFT).exclude(pk=q.pk).order_by("id").first()
                return redirect("panel_question_edit", pk=nxt.pk) if nxt else redirect(reverse("panel_questions") + "?status=draft")
            return redirect("panel_question_edit", pk=q.pk)
    chapters = [{"id": c.pk, "subject": c.subject_id, "name": c.name} for c in Chapter.objects.all()]
    return render(request, "panel/question_form.html", {"nav": nav(request), "form": form, "obj": obj, "chapters": chapters,
                                                       "section": "questions", "problems": obj.problems() if obj else []})


@panel_view()
def question_delete(request, pk):
    q = get_object_or_404(visible(request.user), pk=pk)
    if request.method != "POST" or not roles.can_approve(request.user):
        return render(request, "panel/forbidden.html", {"nav": nav(request)}, status=403)
    try:
        q.delete(); messages.success(request, "Question deleted.")
    except ProtectedError:
        messages.error(request, "This question is used in student tests, so it cannot be deleted. Send it back to draft instead.")
        return redirect("panel_question_edit", pk=pk)
    return redirect("panel_questions")


# ---------------------------------------------------------------- content (tracks, subjects, chapters, banks)
def _kind(kind):
    if kind not in CONTENT:
        raise Http404
    return CONTENT[kind]


def _rows(kind):
    if kind == "tracks":
        qs = Track.objects.annotate(n=Count("subjects", distinct=True))
        return ["Name", "Slug", "Kind", "Order", "Subjects"], [(o, [o.name, o.slug, o.get_kind_display(), o.order, o.n]) for o in qs]
    if kind == "subjects":
        qs = Subject.objects.select_related("track").annotate(c=Count("chapters", distinct=True), n=Count("questions", distinct=True))
        return ["Name", "Track", "Chapters", "Questions"], [(o, [o.name, o.track.name, o.c, o.n]) for o in qs]
    if kind == "chapters":
        qs = Chapter.objects.select_related("subject__track").annotate(n=Count("questions"))
        return ["Name", "Subject", "Order", "Questions"], [(o, [o.name, o.subject.name, o.order, o.n]) for o in qs]
    qs = Source.objects.annotate(n=Count("questions")).order_by("kind", "-year", "name")
    return ["Name", "Kind", "Year", "Logo", "Questions"], [(o, [o.name, o.get_kind_display(), o.year or "", o.logo or "", o.n]) for o in qs]


@panel_view(roles.can_manage_content)
def content_list(request, kind):
    model, fields, title, hint = _kind(kind)
    heads, rows = _rows(kind)
    q = request.GET.get("q", "").strip().lower()
    if q:
        rows = [r for r in rows if q in " ".join(str(c) for c in r[1]).lower()]
    return render(request, "panel/content_list.html", {"nav": nav(request), "kind": kind, "title": title, "hint": hint, "heads": heads,
                                                      "page": page(request, rows, 50), "q": q, "section": kind, "tabs": CONTENT})


@panel_view(roles.can_manage_content)
def content_edit(request, kind, pk=None):
    model, fields, title, hint = _kind(kind)
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = content_form(model, fields)(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save(); messages.success(request, "Saved.")
        return redirect("panel_content", kind=kind)
    return render(request, "panel/content_form.html", {"nav": nav(request), "kind": kind, "title": title, "form": form, "obj": obj, "section": kind})


@panel_view(roles.can_manage_content)
def content_delete(request, kind, pk):
    model = _kind(kind)[0]
    obj = get_object_or_404(model, pk=pk)
    if request.method == "POST":
        try:
            obj.delete(); messages.success(request, "Deleted.")
        except ProtectedError:
            messages.error(request, "It is still used by questions, so it cannot be deleted. Move or remove those first.")
    return redirect("panel_content", kind=kind)


# ---------------------------------------------------------------- users & roles
@panel_view(roles.can_manage_users)
def users(request):
    qs = User.objects.annotate(tests=Count("exams", distinct=True)).prefetch_related("groups").order_by("-date_joined")
    q, r = request.GET.get("q", "").strip(), request.GET.get("role", "")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    rows = [(u, ROLE_NAMES[roles.role(u)], roles.can_manage_user(request.user, u)) for u in qs]
    if r:
        rows = [x for x in rows if x[1].lower() == r]
    return render(request, "panel/users.html", {"nav": nav(request), "page": page(request, rows, 30), "q": q, "role_f": r, "section": "users",
                                                "role_names": [v for v in ROLE_NAMES.values()]})


@panel_view(roles.can_manage_users)
def user_edit(request, pk=None):
    obj = get_object_or_404(User, pk=pk) if pk else None
    if obj and not roles.can_manage_user(request.user, obj):
        messages.error(request, "You cannot change this account." if obj.pk != request.user.pk else "Change your own details from your profile page.")
        return redirect("panel_users")
    form = UserForm(request.POST or None, actor=request.user, instance=obj)
    if request.method == "POST" and form.is_valid():
        u = form.save(); messages.success(request, f"Saved {u.username} as {ROLE_NAMES[roles.role(u)]}.")
        return redirect("panel_users")
    return render(request, "panel/user_form.html", {"nav": nav(request), "form": form, "obj": obj, "section": "users"})
