from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Chapter, Exam, Question, Source, Subject, Track

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
        self.client.post(reverse("exam_profile"), {"first_name": "রাকিব", "last_name": "", "phone": "017", "institution": "X", "target": ""})
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
        self.assertEqual([lab for lab, _ in r.context["other_groups"]], ["বোর্ড"])
