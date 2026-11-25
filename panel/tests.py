from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from exams import roles
from exams.models import Chapter, Question, Source, Subject, Track

User = get_user_model()


def person(name, role=None):
    u = User.objects.create_user(name, f"{name}@x.com", "pw12345!")
    roles.apply_role(u, role)
    return u


class PanelBase(TestCase):
    def setUp(self):
        self.track = Track.objects.create(name="SSC", slug="ssc")
        self.subj = Subject.objects.create(track=self.track, name="Physics")
        self.ch = Chapter.objects.create(subject=self.subj, name="Motion", order=1)
        self.teacher, self.teacher2 = person("t1", roles.TEACHER), person("t2", roles.TEACHER)
        self.mod, self.adm, self.root = person("m1", roles.MODERATOR), person("a1", roles.ADMIN), person("root", "superuser")
        self.student = person("s1")

    def q(self, author, text="Q?", status="draft", **kw):
        return Question.objects.create(subject=self.subj, chapter=self.ch, text=text, option_a="1", option_b="2", option_c="3",
                                       option_d="4", correct="b", status=status, author=author, **kw)

    def post_q(self, **over):
        d = {"qtype": "mcq", "subject": self.subj.pk, "chapter": self.ch.pk, "text": "New question?", "option_a": "a", "option_b": "b",
             "option_c": "c", "option_d": "d", "correct": "c", "action": "save"}
        d.update(over)
        return d


class Access(PanelBase):
    def test_anonymous_goes_to_sign_in_and_students_are_refused(self):
        self.assertEqual(self.client.get(reverse("panel_home")).status_code, 302)
        self.client.force_login(self.student)
        for name in ("panel_home", "panel_questions", "panel_users"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_every_staff_role_opens_the_dashboard_but_only_admins_see_content_and_users(self):
        for u, content, users in ((self.teacher, 403, 403), (self.mod, 403, 403), (self.adm, 200, 200), (self.root, 200, 200)):
            self.client.force_login(u)
            self.assertEqual(self.client.get(reverse("panel_home")).status_code, 200, u.username)
            self.assertEqual(self.client.get(reverse("panel_content", args=["subjects"])).status_code, content, u.username)
            self.assertEqual(self.client.get(reverse("panel_users")).status_code, users, u.username)


class Questions(PanelBase):
    def test_teacher_sees_only_their_own_questions_and_cannot_open_others(self):
        mine, theirs = self.q(self.teacher, "mine"), self.q(self.teacher2, "theirs")
        self.client.force_login(self.teacher)
        r = self.client.get(reverse("panel_questions"))
        self.assertEqual({x.pk for x in r.context["page"]}, {mine.pk})
        self.assertEqual(self.client.get(reverse("panel_question_edit", args=[theirs.pk])).status_code, 404)

    def test_teacher_can_write_but_never_publish(self):
        self.client.force_login(self.teacher)
        r = self.client.post(reverse("panel_question_new"), self.post_q(action="approve"))
        self.assertEqual(r.status_code, 302)
        q = Question.objects.get(text="New question?")
        self.assertEqual((q.status, q.author_id), ("draft", self.teacher.pk))

    def test_teacher_editing_a_published_question_sends_it_back_for_review(self):
        q = self.q(self.teacher, status="approved")
        self.client.force_login(self.teacher)
        self.client.post(reverse("panel_question_edit", args=[q.pk]), self.post_q(text="Edited?"))
        q.refresh_from_db(); self.assertEqual((q.text, q.status), ("Edited?", "draft"))

    def test_moderator_publishes_and_incomplete_questions_are_refused(self):
        good = self.q(self.teacher)
        self.client.force_login(self.mod)
        self.client.post(reverse("panel_question_edit", args=[good.pk]), self.post_q(text=good.text, action="approve"))
        good.refresh_from_db(); self.assertEqual(good.status, "approved")
        bad = self.q(self.teacher, "no answer")
        r = self.client.post(reverse("panel_question_edit", args=[bad.pk]), self.post_q(text="no answer", correct="", action="approve"))
        self.assertEqual(r.status_code, 200); bad.refresh_from_db(); self.assertEqual(bad.status, "draft")

    def test_bulk_actions_need_a_reviewer_role_and_skip_incomplete_questions(self):
        a, b = self.q(self.teacher, "a"), self.q(self.teacher, "b"); b.option_c = ""; b.save()
        self.client.force_login(self.teacher)
        self.client.post(reverse("panel_questions"), {"bulk": "approve", "ids": [a.pk, b.pk]})
        a.refresh_from_db(); self.assertEqual(a.status, "draft")           # teachers cannot bulk publish
        self.client.force_login(self.mod)
        self.client.post(reverse("panel_questions"), {"bulk": "approve", "ids": [a.pk, b.pk]})
        a.refresh_from_db(); b.refresh_from_db(); self.assertEqual((a.status, b.status), ("approved", "draft"))

    def test_creative_question_keeps_parts_and_drops_options(self):
        self.client.force_login(self.teacher)
        d = self.post_q(qtype="cq", text="Stem", p1_q="Define velocity", p1_marks="1", p1_answer="Rate of change of displacement", p2_q="")
        self.client.post(reverse("panel_question_new"), d)
        q = Question.objects.get(text="Stem")
        self.assertEqual(q.parts, [{"q": "Define velocity", "marks": 1, "answer": "Rate of change of displacement"}])
        self.assertEqual((q.option_a, q.correct), ("", ""))

    def test_short_question_keeps_its_solution_and_drops_options(self):
        self.client.force_login(self.teacher)
        d = self.post_q(qtype="sq", text="Find x", explanation="x = 2", p1_q="stray", p1_marks="1")
        self.client.post(reverse("panel_question_new"), d)
        q = Question.objects.get(text="Find x")
        self.assertEqual((q.qtype, q.explanation, q.parts), ("sq", "x = 2", []))
        self.assertEqual((q.option_a, q.correct), ("", ""))
        self.assertEqual(q.problems(), [])                      # an SQ needs no options or parts

    def test_only_reviewers_can_delete(self):
        q = self.q(self.teacher)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(reverse("panel_question_delete", args=[q.pk])).status_code, 403)
        self.client.force_login(self.mod)
        self.client.post(reverse("panel_question_delete", args=[q.pk]))
        self.assertFalse(Question.objects.filter(pk=q.pk).exists())


class Content(PanelBase):
    def test_admin_manages_subjects_chapters_and_banks(self):
        self.client.force_login(self.adm)
        self.client.post(reverse("panel_content_new", args=["subjects"]), {"track": self.track.pk, "name": "Chemistry"})
        self.assertTrue(Subject.objects.filter(name="Chemistry").exists())
        self.client.post(reverse("panel_content_new", args=["banks"]), {"name": "ঢাকা বোর্ড ২০২৫", "kind": "board", "year": 2025, "logo": ""})
        self.assertEqual(Source.objects.get(name="ঢাকা বোর্ড ২০২৫").year, 2025)

    def test_cannot_delete_something_still_in_use(self):
        self.q(self.teacher)
        self.client.force_login(self.adm)
        self.client.post(reverse("panel_content_delete", args=["subjects", self.subj.pk]))
        self.assertTrue(Subject.objects.filter(pk=self.subj.pk).exists())


class Users(PanelBase):
    def test_admin_can_create_a_teacher_but_not_an_admin(self):
        self.client.force_login(self.adm)
        base = {"username": "newt", "email": "n@x.com", "first_name": "", "last_name": "", "password": "Str0ng-pass-91", "is_active": "on"}
        self.client.post(reverse("panel_user_new"), {**base, "role": "Teacher"})
        self.assertEqual(roles.role(User.objects.get(username="newt")), roles.TEACHER)
        r = self.client.post(reverse("panel_user_new"), {**base, "username": "evil", "role": "Admin"})
        self.assertEqual(r.status_code, 200); self.assertFalse(User.objects.filter(username="evil").exists())

    def test_admin_cannot_touch_admins_or_superusers_but_a_superuser_can_make_admins(self):
        self.client.force_login(self.adm)
        for target in (self.root, self.adm):
            self.assertEqual(self.client.get(reverse("panel_user_edit", args=[target.pk])).status_code, 302)
        self.client.force_login(self.root)
        self.client.post(reverse("panel_user_edit", args=[self.mod.pk]), {"username": "m1", "role": "Admin", "is_active": "on", "email": "m@x.com"})
        self.assertEqual(roles.role(User.objects.get(username="m1")), roles.ADMIN)

    def test_changing_a_role_replaces_the_old_one_and_can_disable_or_reset_password(self):
        self.client.force_login(self.adm)
        self.client.post(reverse("panel_user_edit", args=[self.teacher.pk]),
                         {"username": "t1", "role": "Moderator", "email": "t@x.com", "password": "Another-Str0ng-1"})
        u = User.objects.get(username="t1")
        self.assertEqual(list(u.groups.values_list("name", flat=True)), ["Moderator"]); self.assertTrue(u.check_password("Another-Str0ng-1"))
        self.client.post(reverse("panel_user_edit", args=[u.pk]), {"username": "t1", "role": "student", "email": "t@x.com"})   # unticked 'active'
        u.refresh_from_db(); self.assertEqual((roles.role(u), u.is_staff, u.is_active), (None, False, False))

    def test_nobody_edits_their_own_role_here(self):
        self.client.force_login(self.adm)
        self.assertEqual(self.client.get(reverse("panel_user_edit", args=[self.adm.pk])).status_code, 302)
