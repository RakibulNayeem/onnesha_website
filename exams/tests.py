from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Chapter, Exam, Profile, Question, Source, Subject, Track

User = get_user_model()


def mcq(subject, n, chapter=None, source=None, correct="b", status="approved"):
    return Question.objects.create(
        subject=subject, chapter=chapter, source=source, qtype="mcq", text=f"Q{n}",
        option_a="1", option_b="2", option_c="3", option_d="4", correct=correct, status=status)


class ExamFlow(TestCase):
    def setUp(self):
        self.track = Track.objects.create(name="Admission", slug="adm", kind="admission")
        self.subj = Subject.objects.create(track=self.track, name="Physics")
        self.ch = Chapter.objects.create(subject=self.subj, name="Motion")
        self.src = Source.objects.create(name="DU 2023")
        for i in range(6):
            mcq(self.subj, i, self.ch, self.src)
        mcq(self.subj, 99, status="draft")  # must never reach students
        self.user = User.objects.create_user("stu", "s@x.com", "pw12345!")

    def test_pages_render(self):
        for name in ("exam_home", "exam_leaderboard", "exam_cq", "account_login", "account_signup"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        r = self.client.get(reverse("exam_practice"))  # no selection -> start at the subject list
        self.assertRedirects(r, reverse("exam_build") + "?mode=quick", fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("exam_subject", args=[self.subj.id])).status_code, 200)
        r = self.client.get(reverse("exam_practice") + f"?subject={self.subj.id}")
        self.assertContains(r, "Q0")
        self.assertNotContains(r, "Q99")  # drafts never shown

    def test_full_exam_cycle(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("exam_build") + f"?subject={self.subj.id}").status_code, 200)
        r = self.client.post(reverse("exam_build"), {
            "subjects": [self.subj.id], "count": 10, "source": self.src.id})
        exam = Exam.objects.get()
        self.assertRedirects(r, reverse("exam_take", args=[exam.pk]))
        self.assertEqual(exam.items.count(), 6)  # shortened, draft excluded
        self.assertEqual(exam.negative, 0.25)
        self.assertEqual(self.client.get(reverse("exam_take", args=[exam.pk])).status_code, 200)
        ids = list(exam.items.values_list("question_id", flat=True))
        self.client.post(reverse("exam_take", args=[exam.pk]), {
            f"q{ids[0]}": "b", f"q{ids[1]}": "b", f"q{ids[2]}": "a"})
        exam.refresh_from_db()
        self.assertEqual((exam.correct, exam.wrong, exam.skipped), (2, 1, 3))
        self.assertAlmostEqual(exam.score, 1.75)
        self.assertEqual(self.client.get(reverse("exam_result", args=[exam.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("exam_dashboard")).status_code, 200)

    def test_reserved_questions_stay_out_of_the_bank_but_reach_exams(self):
        held = Source.objects.create(name="Model Test 1", kind="other")
        r = mcq(self.subj, 500, source=held)
        r.reserved = True
        r.save()
        page = self.client.get(reverse("exam_practice") + f"?subject={self.subj.id}")
        self.assertNotContains(page, "Q500")                       # not in practice
        self.assertNotContains(self.client.get(reverse("exam_bank")), "Model Test 1")
        self.assertNotContains(self.client.get(reverse("exam_subject", args=[self.subj.id])), "Model Test 1")
        self.client.force_login(self.user)
        self.client.post(reverse("exam_build"), {"subjects": [self.subj.id], "count": 50})
        self.assertIn(r.pk, Exam.objects.get().items.values_list("question_id", flat=True))  # but in exams

    def test_other_students_exam_is_private(self):
        exam = Exam.objects.create(user=self.user, title="t", duration_minutes=5)
        other = User.objects.create_user("o", "o@x.com", "pw12345!")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("exam_take", args=[exam.pk])).status_code, 404)

    def test_hub_is_public_but_starting_a_test_needs_login(self):
        self.assertEqual(self.client.get(reverse("exam_build")).status_code, 200)
        r = self.client.post(reverse("exam_build"), {"subjects": [self.subj.id], "count": 10})
        self.assertIn(reverse("account_login"), r["Location"])
        self.assertEqual(Exam.objects.count(), 0)

    def test_incomplete_question_cannot_be_approved(self):
        q = Question(subject=self.subj, text="x", qtype="mcq", status="approved")
        self.assertTrue(q.problems())


class MixedSelection(TestCase):
    """A subject with ticked chapters is limited to them; one without is taken whole."""
    def setUp(self):
        t = Track.objects.create(name="T", slug="t")
        self.a = Subject.objects.create(track=t, name="A")
        self.b = Subject.objects.create(track=t, name="B")
        self.a1 = Chapter.objects.create(subject=self.a, name="a1")
        self.a2 = Chapter.objects.create(subject=self.a, name="a2")
        mcq(self.a, 1, self.a1); mcq(self.a, 2, self.a2); mcq(self.b, 3); mcq(self.b, 4)

    def test_practice_scope(self):
        url = reverse("exam_practice")
        r = self.client.get(url, {"subject": [self.a.id, self.b.id], "chapter": [self.a1.id]})
        texts = {q.text for q in r.context["page"]}
        self.assertEqual(texts, {"Q1", "Q3", "Q4"})  # A limited to a1, B whole


class Roles(TestCase):
    """Teacher writes (own, drafts only) -> Moderator approves -> Admin manages users -> Superuser owns."""
    def setUp(self):
        from django.contrib.auth.models import Group
        t = Track.objects.create(name="T", slug="t")
        self.subj = Subject.objects.create(track=t, name="S")

        def staff(name, group=None, **kw):
            u = User.objects.create_user(name, f"{name}@x.com", "pw12345!", is_staff=True, **kw)
            if group:
                u.groups.add(Group.objects.get(name=group))
            return u
        self.teacher, self.teacher2 = staff("teach", "Teacher"), staff("teach2", "Teacher")
        self.mod, self.admin_u = staff("mod", "Moderator"), staff("adm", "Admin")
        self.owner = User.objects.create_superuser("boss", "b@x.com", "pw12345!")
        self.q1 = mcq(self.subj, 1, status="draft"); self.q1.author = self.teacher; self.q1.save()
        self.q2 = mcq(self.subj, 2, status="draft"); self.q2.author = self.teacher2; self.q2.save()

    def test_teacher_sees_only_own_questions(self):
        self.client.force_login(self.teacher)
        r = self.client.get("/django-admin/exams/question/")
        self.assertEqual({q.pk for q in r.context["cl"].queryset}, {self.q1.pk})
        self.assertEqual(self.client.get(f"/django-admin/exams/question/{self.q2.pk}/change/").status_code, 302)  # not theirs

    def test_teacher_cannot_publish(self):
        self.client.force_login(self.teacher)
        data = {"subject": self.subj.pk, "qtype": "mcq", "text": "New?", "option_a": "1", "option_b": "2",
                "option_c": "3", "option_d": "4", "correct": "a", "explanation": "", "parts": "[]", "status": "approved"}
        self.client.post("/django-admin/exams/question/add/", data)
        q = Question.objects.get(text="New?")
        self.assertEqual((q.status, q.author_id), ("draft", self.teacher.pk))

    def test_moderator_sees_all_and_can_approve(self):
        self.client.force_login(self.mod)
        r = self.client.get("/django-admin/exams/question/")
        self.assertEqual(r.context["cl"].queryset.count(), 2)
        self.client.post("/django-admin/exams/question/", {"action": "approve", "_selected_action": [self.q1.pk]})
        self.q1.refresh_from_db()
        self.assertEqual(self.q1.status, "approved")

    def test_teacher_cannot_run_approve_action(self):
        self.client.force_login(self.teacher)
        self.client.post("/django-admin/exams/question/", {"action": "approve", "_selected_action": [self.q1.pk]})
        self.q1.refresh_from_db()
        self.assertEqual(self.q1.status, "draft")

    def test_admin_cannot_see_or_create_superusers(self):
        self.client.force_login(self.admin_u)
        r = self.client.get("/django-admin/auth/user/")
        names = {u.username for u in r.context["cl"].queryset}
        self.assertNotIn("boss", names); self.assertNotIn("adm", names)
        self.assertEqual(self.client.get(f"/django-admin/auth/user/{self.owner.pk}/change/").status_code, 302)

    def test_student_cannot_enter_panel(self):
        s = User.objects.create_user("stu9", "s9@x.com", "pw12345!")
        self.client.force_login(s)
        self.assertEqual(self.client.get("/django-admin/").status_code, 302)

    def test_profile_page_saves(self):
        s = User.objects.create_user("stu8", "s8@x.com", "pw12345!")
        self.client.force_login(s)
        self.assertEqual(self.client.get(reverse("exam_profile")).status_code, 200)
        self.client.post(reverse("exam_profile"), {"username": "stu8", "first_name": "রাকিব", "last_name": "", "phone": "017", "institution": "X", "target": ""})
        s.refresh_from_db()
        self.assertEqual((s.first_name, s.profile.phone), ("রাকিব", "017"))


class Notifications(TestCase):
    """Reminders are derived: they stay until the thing they point at is done."""
    def setUp(self):
        self.user = User.objects.create_user("nn", "nn@x.com", "pw12345!")
        self.client.force_login(self.user)
        self.exam = Exam.objects.create(user=self.user, title="Open test", duration_minutes=5)

    def notes(self):
        return self.client.get(reverse("exam_home")).context["hud"]["notes"]

    def test_unfinished_test_stays_until_it_is_finished(self):
        self.assertEqual(len(self.notes()), 1)
        self.assertEqual(len(self.notes()), 1)           # opening the list does not dismiss it
        self.exam.submit({})
        self.assertEqual(self.notes(), [])


class UniversityList(TestCase):
    def test_universities_are_grouped_by_letter_in_order_and_boards_are_separate(self):
        for n in ("খুলনা বিশ্ববিদ্যালয়", "ঢাকা বিশ্ববিদ্যালয়", "কুমিল্লা বিশ্ববিদ্যালয়", "ক্যাম্পাস টেস্ট"):
            Source.objects.create(name=n, kind="university")
        Source.objects.create(name="ঢাকা বোর্ড", kind="board")
        r = self.client.get(reverse("exam_bank") + "?tab=institution")
        groups = r.context["uni_groups"]
        self.assertEqual([g for g, _ in groups], sorted({n[:1] for n in ("খুলনা", "ঢাকা", "কুমিল্লা", "ক্যাম্পাস")}))
        self.assertEqual([s.name for s in dict(groups)["ক"]], sorted(["কুমিল্লা বিশ্ববিদ্যালয়", "ক্যাম্পাস টেস্ট"]))
        self.assertEqual(r.context["other_groups"], [])            # boards now have their own tab
        self.assertEqual(len(r.context["board_groups"]), 1)


class ImportBank(TestCase):
    """The transcribed-book loader: files questions by board+year, skips bad ones, and never duplicates."""
    def make(self, tmp):
        p = Path(tmp) / "c.txt"
        p.write_text("@track ssc এসএসসি academic\n@subject পদার্থবিজ্ঞান\n@chapter 1 ভৌত রাশি\n"
                     "1 || ঢা. বো.'২৩; ব. বো.'২২ || b || প্রশ্ন এক? || ক || খ || গ || ঘ\n"
                     "2 || সম্ভাব্য প্রশ্ন || c || প্রশ্ন দুই? ¶ (i) এ ¶ (ii) বি || এ || বি || সি || ডি\n"
                     "3 || ঢা. বো.'২৪ || x || ভুল প্রশ্ন? || ক || খ || গ || ঘ\n"
                     "4 || সি. বো.'২৩ || a || প্রশ্ন এক? || অন্য || খ || গ || ঘ\n", encoding="utf-8")
        return str(p)

    def test_import_files_by_board_year_and_is_idempotent(self):
        import tempfile
        from django.core.management import call_command
        with tempfile.TemporaryDirectory() as tmp:
            f = self.make(tmp)
            call_command("import_bank", f, verbosity=0); call_command("import_bank", f, verbosity=0)
        self.assertEqual(Question.objects.count(), 3)            # re-run did not duplicate; Q3 skipped; Q4 shares Q1's stem but is its own question
        q1 = Question.objects.get(text="প্রশ্ন এক?", option_a="ক")
        self.assertEqual((q1.source.name, q1.source.year, q1.source.kind), ("ঢাকা বোর্ড ২০২৩", 2023, "board"))
        self.assertEqual((q1.correct, q1.status, q1.refs), ("b", "approved", "ঢা. বো.'২৩; ব. বো.'২২"))
        q2 = Question.objects.get(text__startswith="প্রশ্ন দুই?")
        self.assertIn("\n(i) এ\n", q2.text)                      # ¶ became real line breaks
        self.assertEqual(q2.source.kind, "other")


class LanguageAndAuth(TestCase):
    def test_default_is_bangla_and_switch_sets_a_cookie(self):
        r = self.client.get(reverse("exam_home"))
        self.assertContains(r, 'lang="bn"'); self.assertContains(r, "পরীক্ষার হলের মতো")
        r = self.client.get(reverse("exam_lang", args=["en"]), HTTP_REFERER="http://testserver/bank/")
        self.assertRedirects(r, "http://testserver/bank/", fetch_redirect_response=False)
        self.assertEqual(r.cookies["lang"].value, "en")

    def test_english_interface_translates_text_and_numerals_but_not_content(self):
        t = Track.objects.create(name="এসএসসি", slug="ssc2"); s = Subject.objects.create(track=t, name="পদার্থবিজ্ঞান")
        mcq(s, 1)
        self.client.cookies["lang"] = "en"
        r = self.client.get(reverse("exam_home"))
        self.assertContains(r, 'lang="en"'); self.assertContains(r, "Prepare the way the exam hall feels")
        self.assertContains(r, "পদার্থবিজ্ঞান")                      # subject names are content, left as written
        r = self.client.get(reverse("exam_bank"))
        self.assertContains(r, "Question bank"); self.assertNotContains(r, "প্রশ্নব্যাংক</h1>")
        self.client.cookies["lang"] = "bn"
        self.assertContains(self.client.get(reverse("exam_home")), "পরীক্ষার হলের মতো")

    def test_bogus_language_cookie_falls_back_to_bangla(self):
        self.client.cookies["lang"] = "xx"
        self.assertContains(self.client.get(reverse("exam_home")), 'lang="bn"')

    def test_sign_in_and_sign_up_pages_use_the_branded_layout_and_work(self):
        for name in ("account_login", "account_signup"):
            self.assertContains(self.client.get(reverse(name)), "authcard")
        r = self.client.post(reverse("account_signup"), {"email": "new@x.com", "password1": "Str0ng-pass-91", "password2": "Str0ng-pass-91"})
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(email="new@x.com")
        self.assertTrue(hasattr(u, "profile"))                      # profile created on sign-up
        self.client.logout()
        r = self.client.post(reverse("account_login"), {"login": "new@x.com", "password": "Str0ng-pass-91"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(reverse("exam_profile")).status_code, 200)


class SeedUniversities(TestCase):
    def test_seed_is_idempotent_and_every_logo_file_exists(self):
        from pathlib import Path
        from django.conf import settings
        from django.core.management import call_command
        from exams.management.commands.seed_universities import LOGOS, UNIVERSITIES
        call_command("seed_universities", verbosity=0); call_command("seed_universities", verbosity=0)
        self.assertEqual(Source.objects.filter(kind="university").count(), len(set(UNIVERSITIES)))
        self.assertTrue(set(LOGOS) <= set(UNIVERSITIES))
        for f in LOGOS.values():
            self.assertTrue((Path(settings.BASE_DIR) / "static" / "img" / "logos" / f).exists(), f)


class StaticCacheBusting(TestCase):
    def test_css_and_js_urls_carry_a_content_hash(self):
        import re
        html = self.client.get(reverse("exam_home")).content.decode()
        self.assertRegex(html, r'/static/css/site\.css\?v=[0-9a-f]{10}')
        self.assertRegex(html, r'/static/js/theme\.js\?v=[0-9a-f]{10}')


class SignInWithUsername(TestCase):
    def test_staff_without_an_email_can_sign_in_with_their_username_and_students_with_their_email(self):
        User.objects.create_user("onnesha_admin_rakib", "", "Str0ng-pass-91", is_staff=True)
        r = self.client.post(reverse("account_login"), {"login": "onnesha_admin_rakib", "password": "Str0ng-pass-91"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(reverse("exam_profile")).status_code, 200)
        self.client.logout()
        User.objects.create_user("stu77", "stu77@x.com", "Str0ng-pass-91")
        r = self.client.post(reverse("account_login"), {"login": "stu77@x.com", "password": "Str0ng-pass-91"})
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        r = self.client.post(reverse("account_login"), {"login": "onnesha_admin_rakib", "password": "wrong-password"})
        self.assertEqual(r.status_code, 200)                                # wrong password is still refused


class ImportCQ(TestCase):
    def test_transcribed_cq_files_import_with_ordered_parts_and_are_idempotent(self):
        from pathlib import Path
        from django.core.management import call_command
        files = sorted(str(p) for p in Path("exams/data/ssc_physics").glob("cq*.txt"))
        call_command("import_cq", *files, verbosity=0)
        n = Question.objects.filter(qtype="cq").count()
        call_command("import_cq", *files, verbosity=0)
        self.assertEqual(Question.objects.filter(qtype="cq").count(), n)
        self.assertGreaterEqual(n, 30)
        for q in Question.objects.filter(qtype="cq"):
            self.assertEqual(q.status, "approved")
            self.assertEqual([p["marks"] for p in q.parts], [1, 2, 3, 4])
            self.assertEqual(q.problems(), [])
        self.assertContains(self.client.get("/cq/"), "মধ্যবিন্দু")  # newest CQ is on page 1


class BankTabs(TestCase):
    def test_boards_have_their_own_tab_grouped_by_year(self):
        track = Track.objects.create(name="SSC", slug="ssc", kind="academic")
        subj = Subject.objects.create(track=track, name="Physics")
        for name, year in (("ঢাকা বোর্ড ২০২৪", 2024), ("রাজশাহী বোর্ড ২০২৩", 2023)):
            src = Source.objects.create(name=name, kind="board", year=year)
            mcq(subj, year, source=src)
        Source.objects.create(name="ঢাকা বিশ্ববিদ্যালয়", kind="university")
        board = self.client.get(reverse("exam_bank") + "?tab=board")
        self.assertContains(board, "ঢাকা বোর্ড ২০২৪")
        self.assertContains(board, "রাজশাহী বোর্ড ২০২৩")
        self.assertNotContains(board, "ঢাকা বিশ্ববিদ্যালয়")
        inst = self.client.get(reverse("exam_bank") + "?tab=institution")
        self.assertContains(inst, "ঢাকা বিশ্ববিদ্যালয়")
        self.assertNotContains(inst, "ঢাকা বোর্ড ২০২৪")      # boards moved out of the institution tab
        self.assertEqual(self.client.get(reverse("exam_bank")).status_code, 200)


class StudentProfile(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("stu", "s@x.com", "pw12345!")
        self.client.force_login(self.user)

    def save(self, **extra):
        data = {"username": "stu", "first_name": "Rakib", "last_name": "N", "phone": "", "birth_date": "2010-05-01", "gender": "m",
                "address": "Dhaka", "institution": "Govt School", "level": "ssc", "division": "science",
                "batch_year": "2027", **extra}
        return self.client.post(reverse("exam_profile"), data)

    def test_personal_and_academic_details_are_saved(self):
        self.assertEqual(self.client.get(reverse("exam_profile")).status_code, 200)
        self.assertRedirects(self.save(), reverse("exam_profile"))
        p = Profile.objects.get(user=self.user)
        self.assertEqual((p.level, p.division, p.batch_year, p.gender, p.address),
                         ("ssc", "science", 2027, "m", "Dhaka"))

    def test_school_levels_see_only_subject_and_board_tabs_and_have_no_division_for_junior_classes(self):
        self.save()
        r = self.client.get(reverse("exam_bank") + "?tab=institution")        # not allowed for SSC
        self.assertEqual(r.context["tabs"], ("subject", "board"))
        self.assertEqual(r.context["tab"], "subject")
        self.save(level="c7", division="science")
        self.assertEqual(Profile.objects.get(user=self.user).division, "")                      # classes 6-8 have no division
        self.save(level="hsc")
        r = self.client.get(reverse("exam_bank") + "?tab=institution")
        self.assertEqual(r.context["tabs"], ("subject", "board", "institution"))
        self.assertEqual(r.context["tab"], "institution")

    def test_visitors_without_a_level_see_every_tab(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("exam_bank")).context["tabs"], ("subject", "board", "institution"))


class BackButtons(TestCase):
    def test_inner_pages_have_a_back_arrow(self):
        track = Track.objects.create(name="SSC", slug="ssc", kind="academic")
        subj = Subject.objects.create(track=track, name="Physics")
        mcq(subj, 1)
        user = User.objects.create_user("b", "b@x.com", "pw12345!")
        self.client.force_login(user)
        for url in (reverse("exam_subject", args=[subj.id]), reverse("exam_track", args=[track.slug]),
                    reverse("exam_practice") + f"?subject={subj.id}", reverse("exam_cq"), reverse("exam_bank"),
                    reverse("exam_dashboard"), reverse("exam_profile"), reverse("exam_leaderboard")):
            self.assertContains(self.client.get(url), 'class="back"', msg_prefix=url)


class UsernameEdit(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("stu", "s@x.com", "pw12345!")
        User.objects.create_user("Taken", "t@x.com", "pw12345!")
        self.client.force_login(self.user)

    def test_username_can_be_changed_but_not_to_a_taken_one(self):
        base = {"first_name": "", "last_name": "", "phone": "", "birth_date": "", "gender": "", "address": "",
                "institution": "", "level": "", "division": "", "batch_year": ""}
        r = self.client.post(reverse("exam_profile"), {**base, "username": "taken"})   # case-insensitive clash
        self.assertContains(r, "আগেই নেওয়া হয়েছে")
        self.assertRedirects(self.client.post(reverse("exam_profile"), {**base, "username": "new_name"}),
                             reverse("exam_profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new_name")

    def test_live_check(self):
        url = reverse("exam_username_check")
        self.assertTrue(self.client.get(url, {"u": "free_name"}).json()["ok"])
        self.assertFalse(self.client.get(url, {"u": "TAKEN"}).json()["ok"])
        self.assertFalse(self.client.get(url, {"u": "bad name!"}).json()["ok"])
        self.assertTrue(self.client.get(url, {"u": "stu"}).json()["ok"])             # your own name is fine
