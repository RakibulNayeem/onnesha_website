from django.contrib import messages
from django.db.models import Count, Min, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import ClassLevel, Course, Program, Student, Subject, Teacher

from .forms import AdmissionApplicationForm, ContactForm, ResultLookupForm
from .i18n import t
from .models import (
    BlogPost, Download, DownloadCategory, Exam, ExamResult, GalleryAlbum,
    GalleryImage, HeroSlide, Notice, SiteSettings, VideoLecture,
)


def _lang(request):
    return request.session.get("lang", "en")


def set_language(request, code):
    if code in ("en", "bn"):
        request.session["lang"] = code
    return redirect(request.META.get("HTTP_REFERER") or "pub_home")


def home(request):
    programs = Program.objects.filter(is_active=True, show_on_website=True)
    teachers = Teacher.objects.filter(show_on_website=True)[:8]
    notices = Notice.objects.live()[:5]
    videos = VideoLecture.objects.live().filter(is_short=False)[:3]
    images = GalleryImage.objects.filter(
        is_published=True
    ).exclude(image="", image_url="")[:8]
    posts = BlogPost.objects.live()[:3]
    exams = Exam.objects.live()[:3]
    slides = HeroSlide.objects.filter(is_published=True).exclude(
        image="", image_url=""
    )

    fee_from = (
        Course.objects.filter(is_active=True)
        .values("program")
        .annotate(low=Min("monthly_fee"))
    )
    fee_map = {row["program"]: row["low"] for row in fee_from}

    slides = HeroSlide.objects.filter(is_published=True).exclude(
        image="", image_url=""
    )

    return render(request, "website/home.html", {
        "slides": slides,
        "programs": programs, "teachers": teachers, "notices": notices,
        "videos": videos, "images": images, "posts": posts, "exams": exams,
        "fee_map": fee_map, "slides": slides,
    })


def programs(request):
    programs = Program.objects.filter(is_active=True, show_on_website=True)
    data = []
    for p in programs:
        courses = Course.objects.filter(
            program=p, is_active=True
        ).select_related("subject").order_by("class_level", "subject__name")
        levels = {}
        for c in courses:
            levels.setdefault(c.get_class_level_display(), []).append(c)
        data.append({"program": p, "levels": levels, "count": courses.count()})
    return render(request, "website/programs.html", {"data": data})


def program_detail(request, pk):
    program = get_object_or_404(
        Program, pk=pk, is_active=True, show_on_website=True
    )
    courses = Course.objects.filter(
        program=program, is_active=True
    ).select_related("subject", "teacher").order_by("class_level", "subject__name")
    levels = {}
    for c in courses:
        levels.setdefault(c.get_class_level_display(), []).append(c)
    return render(request, "website/program_detail.html", {
        "program": program, "levels": levels,
        "teachers": Teacher.objects.filter(
            show_on_website=True, courses__program=program
        ).distinct(),
        "others": Program.objects.filter(
            is_active=True, show_on_website=True
        ).exclude(pk=program.pk),
    })


def teachers(request):
    return render(request, "website/teachers.html", {
        "teachers": Teacher.objects.filter(show_on_website=True),
    })


def notice_list(request):
    return render(request, "website/notice_list.html", {
        "notices": Notice.objects.live(),
    })


def notice_detail(request, pk):
    notice = get_object_or_404(Notice.objects.live(), pk=pk)
    return render(request, "website/notice_detail.html", {
        "notice": notice,
        "others": Notice.objects.live().exclude(pk=pk)[:6],
    })


def result_index(request):
    return render(request, "website/result_index.html", {
        "exams": Exam.objects.live(),
        "form": ResultLookupForm(),
    })


def result_detail(request, pk):
    exam = get_object_or_404(Exam.objects.live(), pk=pk)
    form = ResultLookupForm(request.GET or None)
    found = None
    not_found = False

    if form.is_bound and form.is_valid():
        sid = form.cleaned_data["student_id"].strip()
        found = ExamResult.objects.filter(
            exam=exam, student__student_id__iexact=sid
        ).select_related("student").prefetch_related("subject_marks__subject").first()
        not_found = found is None

    merit = []
    if exam.show_public_list:
        merit = exam.results.select_related("student").all()

    return render(request, "website/result_detail.html", {
        "exam": exam, "form": form, "found": found, "not_found": not_found,
        "merit": merit, "total_students": exam.results.count(),
    })


def gallery(request):
    albums = GalleryAlbum.objects.filter(is_published=True).prefetch_related("images")
    loose = GalleryImage.objects.filter(
        is_published=True, album__isnull=True
    ).exclude(image="", image_url="")
    return render(request, "website/gallery.html", {
        "albums": albums, "loose": loose,
    })


def videos(request):
    kind = request.GET.get("kind", "")
    qs = VideoLecture.objects.live().select_related("subject", "teacher")
    if kind == "short":
        qs = qs.filter(is_short=True)
    elif kind == "lecture":
        qs = qs.filter(is_short=False)
    subject = request.GET.get("subject", "")
    if subject:
        qs = qs.filter(subject_id=subject)
    return render(request, "website/videos.html", {
        "videos": qs, "kind": kind, "subject": subject,
        "subjects": Subject.objects.filter(is_active=True),
    })


def downloads(request):
    category = request.GET.get("category", "")
    qs = Download.objects.live()
    if category:
        qs = qs.filter(category=category)
    return render(request, "website/downloads.html", {
        "downloads": qs, "categories": DownloadCategory.choices,
        "category": category,
    })


def blog_list(request):
    return render(request, "website/blog_list.html", {
        "posts": BlogPost.objects.live().select_related("author"),
    })


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost.objects.live(), slug=slug)
    return render(request, "website/blog_detail.html", {
        "post": post,
        "others": BlogPost.objects.live().exclude(pk=post.pk)[:4],
    })


def admission(request):
    lang = _lang(request)
    if request.method == "POST":
        form = AdmissionApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, t("thanks_application", lang))
            return redirect("pub_admission")
    else:
        form = AdmissionApplicationForm()
    return render(request, "website/admission.html", {
        "form": form,
        "programs": Program.objects.filter(is_active=True, show_on_website=True),
    })


def contact(request):
    lang = _lang(request)
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, t("thanks_message", lang))
            return redirect("pub_contact")
    else:
        form = ContactForm()
    return render(request, "website/contact.html", {"form": form})


def about(request):
    return render(request, "website/about.html", {
        "teachers": Teacher.objects.filter(show_on_website=True)[:6],
        "programs": Program.objects.filter(is_active=True, show_on_website=True),
    })
