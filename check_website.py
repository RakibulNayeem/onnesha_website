import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onnesha_finance.settings")
django.setup()
from django.test import Client
from website.models import BlogPost, Exam, Notice, AdmissionApplication, ContactMessage
from core.models import Student

c = Client()   # anonymous - the public site must work logged out
notice = Notice.objects.first()
post = BlogPost.objects.first()
exam = Exam.objects.first()
student = Student.objects.filter(exam_results__isnull=False).first()

urls = ["/", "/programs/", "/teachers/", "/notices/", f"/notices/{notice.pk}/",
        "/results/", f"/results/{exam.pk}/",
        f"/results/{exam.pk}/?student_id={student.student_id}",
        f"/results/{exam.pk}/?student_id=NOT-A-REAL-ID",
        "/gallery/", "/videos/", "/videos/?kind=short", "/downloads/",
        "/blog/", f"/blog/{post.slug}/", "/admission/", "/contact/", "/about/",
        "/lang/bn/", "/lang/en/"]
bad = []
for u in urls:
    r = c.get(u, follow=True)
    if r.status_code != 200:
        bad.append((u, r.status_code))
    else:
        print(f"  200  {u}")

# Bengali toggle actually changes the page
c.get("/lang/bn/")
bn = c.get("/").content.decode()
assert "\u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be" in bn, "Bengali content missing"
print("bilingual toggle OK")
c.get("/lang/en/")

# result lookup shows only that student
r = c.get(f"/results/{exam.pk}/?student_id={student.student_id}")
body = r.content.decode()
assert student.name in body, "own result not shown"
print("result lookup OK ->", student.student_id)

# admission form
before = AdmissionApplication.objects.count()
r = c.post("/admission/", {"name": "Test Applicant", "class_level": "10",
                           "phone": "01711111111", "message": "interested"})
assert AdmissionApplication.objects.count() == before + 1, f"application failed {r.status_code}"
print("admission form OK")

# short phone must be rejected
r = c.post("/admission/", {"name": "Bad", "class_level": "10", "phone": "123"})
assert AdmissionApplication.objects.count() == before + 1, "bad phone accepted!"
print("phone validation OK")

# contact form + honeypot
before_c = ContactMessage.objects.count()
c.post("/contact/", {"name": "Guardian", "phone": "01722222222", "message": "hello"})
assert ContactMessage.objects.count() == before_c + 1, "contact failed"
c.post("/contact/", {"name": "Bot", "message": "spam", "website": "http://spam"})
assert ContactMessage.objects.count() == before_c + 1, "honeypot let spam through!"
print("contact form + spam trap OK")

# unpublished exams must stay hidden
exam.is_published = False
exam.save()
assert c.get(f"/results/{exam.pk}/").status_code == 404, "unpublished exam visible!"
exam.is_published = True
exam.save()
print("unpublished exam hidden OK")

# the finance system must still require login
r = c.get("/manage/", follow=True)
assert "login" in r.request["PATH_INFO"] or b"Log in" in r.content, "finance system exposed!"
print("staff area still protected OK")

# carousel renders and programme cards link through
home = c.get("/").content.decode()
assert "heroCarousel" in home, "carousel missing"
assert "#program-" in home, "programme cards not clickable"
print("carousel + clickable programme cards OK")

# no staff-login link anywhere on the public site
for u in ["/", "/about/", "/contact/", "/programs/"]:
    body = c.get(u).content.decode()
    assert "/manage/" not in body, f"staff link leaked on {u}"
print("no staff login link on public pages OK")

print()
print("FAILURES:", bad if bad else "none")
