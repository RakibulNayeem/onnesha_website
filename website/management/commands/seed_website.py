"""Fill the public website with realistic starter content."""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Program, Student, Subject, Teacher
from website.models import (
    BlogPost, HeroSlide, Download, DownloadCategory, Exam, ExamResult, GalleryAlbum,
    GalleryImage, Notice, SiteSettings, SubjectMark, VideoLecture,
)


class Command(BaseCommand):
    help = "Create demo notices, videos, gallery, blog posts, exams and results."

    @transaction.atomic
    def handle(self, *args, **opts):
        s = SiteSettings.load()
        s.hero_title_bn = "\u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be"
        s.hero_title_en = "Onnesha"
        s.hero_subtitle_bn = (
            "\u098f\u0995\u09be\u09a1\u09c7\u09ae\u09bf\u0995 \u098f\u09a8\u09cd\u09a1 \u098f\u09a1\u09ae\u09bf\u09b6\u09a8 \u0995\u09c7\u09df\u09be\u09b0 \u2014 "
            "\u09a8\u09ae \u09b6\u09cd\u09b0\u09c7\u09a3\u09bf \u09a5\u09c7\u0995\u09c7 \u09a6\u09cd\u09ac\u09be\u09a6\u09b6, \u098f\u09b8\u098f\u09b8\u09b8\u09bf, \u098f\u0987\u099a\u098f\u09b8\u09b8\u09bf \u0993 "
            "\u09ad\u09b0\u09cd\u09a4\u09bf \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0 \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf\u0964"
        )
        s.hero_subtitle_en = (
            "Academic and admission care - preparation for Class 8 to 12, "
            "SSC, HSC and university admission tests."
        )
        s.about_bn = (
            "\u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be \u098f\u0995\u099f\u09bf \u09b8\u09cd\u09ac\u09aa\u09cd\u09a8 \u09a5\u09c7\u0995\u09c7 \u09b6\u09c1\u09b0\u09c1 \u09b9\u0993\u09df\u09be \u09aa\u09cd\u09b0\u09a4\u09bf\u09b7\u09cd\u09a0\u09be\u09a8 \u2014 "
            "\u09af\u09c7\u0996\u09be\u09a8\u09c7 \u09aa\u09cd\u09b0\u09a4\u09bf\u099f\u09bf \u09b6\u09bf\u0995\u09cd\u09b7\u09be\u09b0\u09cd\u09a5\u09c0 \u09a8\u09be\u09ae \u09a8\u09df, \u09aa\u09b0\u09bf\u099a\u09df \u09aa\u09be\u09df\u0964 "
            "\u099b\u09cb\u099f \u09ac\u09cd\u09af\u09be\u099a, \u09a8\u09bf\u09df\u09ae\u09bf\u09a4 \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be \u0986\u09b0 \u0985\u09ad\u09bf\u09ad\u09be\u09ac\u0995\u09c7\u09b0 \u09b8\u09be\u09a5\u09c7 \u09a8\u09bf\u09af\u09bc\u09ae\u09bf\u09a4 "
            "\u09af\u09cb\u0997\u09be\u09af\u09cb\u0997 \u2014 \u098f\u0987 \u09a4\u09bf\u09a8\u099f\u09bf \u0995\u09a5\u09be\u09b0 \u0989\u09aa\u09b0 \u0986\u09ae\u09b0\u09be \u09a6\u09be\u0981\u09dc\u09bf\u09df\u09c7 \u0986\u099b\u09bf\u0964"
        )
        s.about_en = (
            "Onnesha started with one idea: that a student should be known, "
            "not counted. We keep batches small, test regularly, and talk to "
            "guardians every month about what is actually happening."
        )
        s.address_bn = "\u099a\u09cc\u09a7\u09c1\u09b0\u09c0\u09aa\u09be\u09dc\u09be, \u099f\u09be\u0989\u09a8 \u0995\u09b2\u09cb\u09a8\u09bf \u099a\u09be\u09b0\u09ae\u09be\u09a5\u09be, \u09b6\u09c7\u09b0\u09aa\u09c1\u09b0, \u09ac\u0997\u09c1\u09dc\u09be"
        s.address_en = "Chowdhurypara, Town Colony Charmatha, Sherpur, Bogura"
        s.established_year = "2026"
        s.students_count = "120+"
        s.teachers_count = "8"
        s.success_rate = "94%"
        s.save()

        # programme public copy
        blurbs = {
            "Academic": ("\u09b8\u09cd\u0995\u09c1\u09b2\u09c7\u09b0 \u09aa\u09be\u09a0\u09cd\u09af\u09b8\u09c2\u099a\u09bf \u09a7\u09be\u09aa\u09c7 \u09a7\u09be\u09aa\u09c7",
                         "Step-by-step support for the school syllabus", "book"),
            "SSC Preparation": ("\u098f\u09b8\u098f\u09b8\u09b8\u09bf\u09a4\u09c7 \u09aa\u09c2\u09b0\u09cd\u09a3 \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf",
                                "Complete SSC board preparation", "journal-check"),
            "HSC Preparation": ("\u098f\u0987\u099a\u098f\u09b8\u09b8\u09bf\u09b0 \u099c\u09a8\u09cd\u09af \u0997\u09ad\u09c0\u09b0 \u09aa\u09be\u09a0",
                                "Deep subject work for HSC", "mortarboard"),
            "Admission Test": ("\u09ac\u09bf\u09b6\u09cd\u09ac\u09ac\u09bf\u09a6\u09cd\u09af\u09be\u09b2\u09df \u09ad\u09b0\u09cd\u09a4\u09bf \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be",
                               "University admission test coaching", "rocket-takeoff"),
        }
        bn_names = {
            "Academic": "\u098f\u0995\u09be\u09a1\u09c7\u09ae\u09bf\u0995",
            "SSC Preparation": "\u098f\u09b8\u098f\u09b8\u09b8\u09bf \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf",
            "HSC Preparation": "\u098f\u0987\u099a\u098f\u09b8\u09b8\u09bf \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf",
            "Admission Test": "\u09ad\u09b0\u09cd\u09a4\u09bf \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be",
        }
        for p in Program.objects.all():
            if p.name in blurbs:
                bn, en, icon = blurbs[p.name]
                p.name_bn = bn_names.get(p.name, "")
                p.tagline_bn, p.tagline_en, p.icon = bn, en, icon
                p.show_on_website = True
                p.save()

        # teachers on the website
        desig = [
            ("\u09aa\u09cd\u09b0\u09a7\u09be\u09a8 \u09b6\u09bf\u0995\u09cd\u09b7\u0995", "Head of Physics"),
            ("\u09b8\u09bf\u09a8\u09bf\u09df\u09b0 \u09b6\u09bf\u0995\u09cd\u09b7\u0995", "Senior Teacher"),
        ]
        for i, t in enumerate(Teacher.objects.all()):
            t.show_on_website = True
            t.display_order = i
            t.designation_bn, t.designation_en = desig[i % len(desig)]
            t.qualification_bn = "\u09ac\u09bf.\u098f\u09b8\u09b8\u09bf (\u09aa\u09cd\u09b0\u0995\u09cc\u09b6\u09b2), \u09b0\u09c1\u09df\u09c7\u099f"
            t.qualification_en = "B.Sc. in Engineering, RUET"
            t.bio_en = ("Teaches with a focus on concept first, formula second. "
                        "Has been coaching board and admission students since 2019.")
            t.bio_bn = ("\u09b8\u09c2\u09a4\u09cd\u09b0\u09c7\u09b0 \u0986\u0997\u09c7 \u0995\u09a8\u09b8\u09c7\u09aa\u09cd\u099f \u2014 \u098f\u0987 \u09aa\u09a6\u09cd\u09a7\u09a4\u09bf\u09a4\u09c7 \u09aa\u09dc\u09be\u09a8\u0964 "
                        "\u09e8\u09e6\u09e7\u09ef \u09b8\u09be\u09b2 \u09a5\u09c7\u0995\u09c7 \u09ac\u09cb\u09b0\u09cd\u09a1 \u0993 \u09ad\u09b0\u09cd\u09a4\u09bf \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0\u09cd\u09a5\u09c0\u09a6\u09c7\u09b0 \u09aa\u09dc\u09be\u099a\u09cd\u099b\u09c7\u09a8\u0964")
            t.save()

        slides = [
            ("\u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be \u2014 \u099c\u09be\u09a8\u09be\u09b0 \u09aa\u09a5",
             "Onnesha - the path to knowing",
             "\u099b\u09cb\u099f \u09ac\u09cd\u09af\u09be\u099a, \u09a8\u09bf\u09df\u09ae\u09bf\u09a4 \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be \u0986\u09b0 \u09aa\u09cd\u09b0\u09a4\u09bf\u099c\u09a8 \u09b6\u09bf\u0995\u09cd\u09b7\u09be\u09b0\u09cd\u09a5\u09c0\u09b0 \u099c\u09a8\u09cd\u09af \u0986\u09b2\u09be\u09a6\u09be \u09af\u09a4\u09cd\u09a8\u0964",
             "Small batches, regular tests, and individual attention for every student.",
             "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=1600",
             "\u098f\u0996\u09a8\u0987 \u0986\u09ac\u09c7\u09a6\u09a8 \u0995\u09b0\u09c1\u09a8", "Apply now", "/admission/"),
            ("\u098f\u09b8\u098f\u09b8\u09b8\u09bf \u0993 \u098f\u0987\u099a\u098f\u09b8\u09b8\u09bf \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf",
             "SSC and HSC preparation",
             "\u09ac\u09cb\u09b0\u09cd\u09a1 \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0 \u099c\u09a8\u09cd\u09af \u09aa\u09c2\u09b0\u09cd\u09a3 \u09b8\u09bf\u09b2\u09c7\u09ac\u09be\u09b8 \u0993 \u09b8\u09be\u09aa\u09cd\u09a4\u09be\u09b9\u09bf\u0995 \u09ae\u09a1\u09c7\u09b2 \u099f\u09c7\u09b8\u09cd\u099f\u0964",
             "Full syllabus coverage and weekly model tests for the board exams.",
             "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=1600",
             "\u09aa\u09cd\u09b0\u09cb\u0997\u09cd\u09b0\u09be\u09ae \u09a6\u09c7\u0996\u09c1\u09a8", "See programs", "/programs/"),
            ("\u09ad\u09b0\u09cd\u09a4\u09bf \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0 \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf",
             "Admission test coaching",
             "\u09ac\u09bf\u09b6\u09cd\u09ac\u09ac\u09bf\u09a6\u09cd\u09af\u09be\u09b2\u09df \u09ad\u09b0\u09cd\u09a4\u09bf \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0 \u099c\u09a8\u09cd\u09af \u09a8\u09bf\u09ac\u09bf\u09dc \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf\u0964",
             "Focused preparation for university admission tests.",
             "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=1600",
             "\u09ac\u09bf\u09b8\u09cd\u09a4\u09be\u09b0\u09bf\u09a4", "Read more", "/about/"),
        ]
        for i, (bt, et, bs_, es, img, bbtn, ebtn, url) in enumerate(slides):
            HeroSlide.objects.get_or_create(
                title_en=et,
                defaults=dict(title_bn=bt, subtitle_bn=bs_, subtitle_en=es,
                              image_url=img, button_text_bn=bbtn,
                              button_text_en=ebtn, button_url=url, order=i),
            )

        now = timezone.now()
        notices = [
            ("\u09ad\u09b0\u09cd\u09a4\u09bf \u099a\u09b2\u099b\u09c7 \u2014 \u09a8\u09a4\u09c1\u09a8 \u09ac\u09cd\u09af\u09be\u099a",
             "Admission open - new batch starting",
             "\u09a8\u09ae \u09a5\u09c7\u0995\u09c7 \u09a6\u09cd\u09ac\u09be\u09a6\u09b6 \u09b6\u09cd\u09b0\u09c7\u09a3\u09bf\u09b0 \u09a8\u09a4\u09c1\u09a8 \u09ac\u09cd\u09af\u09be\u099a \u09b6\u09c1\u09b0\u09c1 \u09b9\u099a\u09cd\u099b\u09c7\u0964 "
             "\u0986\u09b8\u09a8 \u09b8\u09c0\u09ae\u09bf\u09a4, \u0986\u0997\u09c7 \u0986\u09b8\u09b2\u09c7 \u0986\u0997\u09c7 \u09ad\u09bf\u09a4\u09cd\u09a4\u09bf\u09a4\u09c7 \u09ad\u09b0\u09cd\u09a4\u09bf \u0995\u09b0\u09be \u09b9\u09ac\u09c7\u0964",
             "New batches for Class 9 to 12 are starting this month. Seats are "
             "limited and filled in order of application.", True),
            ("\u09b8\u09be\u09aa\u09cd\u09a4\u09be\u09b9\u09bf\u0995 \u09ae\u09a1\u09c7\u09b2 \u099f\u09c7\u09b8\u09cd\u099f\u09c7\u09b0 \u09b0\u09c1\u099f\u09bf\u09a8",
             "Weekly model test routine",
             "\u09aa\u09cd\u09b0\u09a4\u09bf \u09b6\u09c1\u0995\u09cd\u09b0\u09ac\u09be\u09b0 \u09b8\u0995\u09be\u09b2 \u09ef\u099f\u09be\u09df \u09ae\u09a1\u09c7\u09b2 \u099f\u09c7\u09b8\u09cd\u099f \u0985\u09a8\u09c1\u09b7\u09cd\u09a0\u09bf\u09a4 \u09b9\u09ac\u09c7\u0964",
             "Model tests are held every Friday at 9:00 AM.", False),
            ("\u09aa\u09c2\u099c\u09be\u09b0 \u099b\u09c1\u099f\u09bf\u09b0 \u09a8\u09cb\u099f\u09bf\u09b6", "Holiday notice",
             "\u09aa\u09c2\u099c\u09be \u0989\u09aa\u09b2\u0995\u09cd\u09b7\u09c7 \u09aa\u09be\u0981\u099a \u09a6\u09bf\u09a8 \u0995\u09cd\u09b2\u09be\u09b8 \u09ac\u09a8\u09cd\u09a7 \u09a5\u09be\u0995\u09ac\u09c7\u0964",
             "Classes will remain closed for five days.", False),
        ]
        for bn_t, en_t, bn_b, en_b, pin in notices:
            Notice.objects.get_or_create(
                title_en=en_t,
                defaults=dict(title_bn=bn_t, body_bn=bn_b, body_en=en_b,
                              is_pinned=pin,
                              published_at=now - timedelta(days=random.randint(1, 20))),
            )

        vids = [
            ("\u09a8\u09bf\u0989\u099f\u09a8\u09c7\u09b0 \u09a4\u09c3\u09a4\u09c0\u09df \u09b8\u09c2\u09a4\u09cd\u09b0", "Newton's third law explained",
             "https://www.youtube.com/watch?v=cP0Bb3WXJ_k", "Physics", False),
            ("\u09b2\u0997\u09be\u09b0\u09bf\u09a6\u09ae \u2014 \u09ac\u09c7\u09b8\u09bf\u0995", "Logarithm basics",
             "https://www.youtube.com/watch?v=cEvgcoyZvB4", "Higher Math", False),
            ("\u09e9\u09e6 \u09b8\u09c7\u0995\u09c7\u09a8\u09cd\u09a1\u09c7 \u098f\u0995\u099f\u09bf \u099f\u09bf\u09aa\u09b8", "One tip in 30 seconds",
             "https://www.youtube.com/shorts/8Xk9Y2vC1Qk", "ICT", True),
        ]
        for bn_t, en_t, url, subj, short in vids:
            VideoLecture.objects.get_or_create(
                youtube_url=url,
                defaults=dict(title_bn=bn_t, title_en=en_t, is_short=short,
                              subject=Subject.objects.filter(name=subj).first()),
            )

        album, _ = GalleryAlbum.objects.get_or_create(
            title_en="Model test day",
            defaults=dict(title_bn="\u09ae\u09a1\u09c7\u09b2 \u099f\u09c7\u09b8\u09cd\u099f\u09c7\u09b0 \u09a6\u09bf\u09a8", held_on=date.today()),
        )
        placeholders = [
            "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800",
            "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=800",
            "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=800",
            "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800",
        ]
        for i, url in enumerate(placeholders):
            GalleryImage.objects.get_or_create(
                album=album, image_url=url,
                defaults=dict(order=i, caption_en="Classroom", caption_bn="\u0995\u09cd\u09b2\u09be\u09b8\u09b0\u09c1\u09ae"),
            )

        for cat, bn_t, en_t in [
            (DownloadCategory.ROUTINE, "\u0995\u09cd\u09b2\u09be\u09b8 \u09b0\u09c1\u099f\u09bf\u09a8", "Class routine"),
            (DownloadCategory.SYLLABUS, "\u09b8\u09bf\u09b2\u09c7\u09ac\u09be\u09b8", "Syllabus"),
            (DownloadCategory.QUESTION, "\u0997\u09a4 \u09ac\u099b\u09b0\u09c7\u09b0 \u09aa\u09cd\u09b0\u09b6\u09cd\u09a8", "Last year's questions"),
        ]:
            Download.objects.get_or_create(
                title_en=en_t, defaults=dict(title_bn=bn_t, category=cat),
            )

        posts = [
            ("\u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be\u09b0 \u0986\u0997\u09c7 \u09b6\u09c7\u09b7 \u09b8\u09be\u09a4 \u09a6\u09bf\u09a8",
             "The last seven days before an exam",
             "\u09b6\u09c7\u09b7 \u09b8\u09aa\u09cd\u09a4\u09be\u09b9\u09c7 \u09a8\u09a4\u09c1\u09a8 \u0995\u09bf\u099b\u09c1 \u09aa\u09dc\u09be\u09b0 \u099a\u09c7\u09df\u09c7 \u09aa\u09c1\u09b0\u09a8\u09cb\u099f\u09be \u0997\u09c1\u099b\u09bf\u09df\u09c7 \u09a8\u09c7\u0993\u09df\u09be \u09ad\u09be\u09b2\u09cb\u0964",
             "In the final week, organising what you already know beats starting "
             "something new."),
            ("\u0997\u09a3\u09bf\u09a4\u09c7 \u09ad\u09df \u0995\u09be\u099f\u09be\u09a8\u09cb\u09b0 \u09909\u09aa\u09be\u09df",
             "Getting over the fear of maths",
             "\u09aa\u09cd\u09b0\u09a4\u09bf\u09a6\u09bf\u09a8 \u09aa\u09cd\u09b0\u09be\u0995\u09cd\u099f\u09bf\u09b8 \u2014 \u09a4\u09be\u09b0 \u0995\u09cb\u09a8\u09cb \u09ac\u09bf\u0995\u09b2\u09cd\u09aa \u09a8\u09c7\u0987\u0964",
             "Daily practice is the only route. There is no shortcut worth taking."),
        ]
        for bn_t, en_t, bn_b, en_b in posts:
            BlogPost.objects.get_or_create(
                title_en=en_t,
                defaults=dict(title_bn=bn_t, body_bn=bn_b, body_en=en_b,
                              excerpt_bn=bn_b[:120], excerpt_en=en_b[:120],
                              author=Teacher.objects.first()),
            )

        # an exam with results, only for students who exist
        students = list(Student.objects.filter(class_level="10")[:10])
        if students:
            exam, created = Exam.objects.get_or_create(
                name_en="Model Test 1",
                defaults=dict(
                    name_bn="\u09ae\u09a1\u09c7\u09b2 \u099f\u09c7\u09b8\u09cd\u099f \u09e7", class_level="10",
                    held_on=date.today() - timedelta(days=7),
                    total_marks=100, is_published=True, show_public_list=True,
                ),
            )
            subjects = list(Subject.objects.filter(
                name__in=["Physics", "Chemistry", "Higher Math"]))
            for i, st in enumerate(students):
                marks = [Decimal(random.randint(18, 33)) for _ in subjects]
                res, _ = ExamResult.objects.get_or_create(
                    exam=exam, student=st,
                    defaults=dict(roll=f"{101 + i}", obtained_marks=sum(marks)),
                )
                for sub, m in zip(subjects, marks):
                    SubjectMark.objects.get_or_create(
                        result=res, subject=sub,
                        defaults=dict(marks=m, out_of=34),
                    )
            exam.rank_results()

        self.stdout.write(self.style.SUCCESS(
            "Public website content seeded. Visit / to see it."))
