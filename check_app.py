"""Smoke test for the staff finance system (now served under /manage/)."""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onnesha_finance.settings")
django.setup()
from django.test import Client
from core.models import (Student, MonthlyEnrollment, Payment, Teacher, Course,
                         Batch, Expense, add_months, month_start)

M = "/manage"
c = Client()
assert c.login(username="admin", password="onnesha123"), "login failed"

s = Student.objects.first()
e = MonthlyEnrollment.objects.first()
p = Payment.objects.first()
t = Teacher.objects.first()
co = Course.objects.first()
b = Batch.objects.first()
m = month_start().strftime("%Y-%m")

urls = [
    "/", f"/?month={m}",
    "/students/", f"/students/?q=Tasnim&batch={b.pk}",
    "/students/new/", f"/students/{s.pk}/", f"/students/{s.pk}/edit/",
    "/enrollment/", f"/enrollment/?month={m}&pay=unpaid",
    "/enrollment/new/", f"/enrollment/new/?student={s.pk}&month={m}",
    f"/enrollment/{e.pk}/edit/",
    "/fees/collect/", f"/fees/collect/?student={s.pk}&month={m}",
    "/fees/", f"/fees/?scope=for_month&month={m}", f"/fees/{p.pk}/receipt/",
    "/expenses/", "/teachers/", "/teachers/new/", f"/teachers/{t.pk}/edit/",
    f"/teachers/pay/?teacher={t.pk}&month={m}",
    "/attendance/", f"/attendance/?batch={b.pk}", "/attendance/report/",
    "/reports/dues/", f"/reports/dues/?scope=month&month={m}",
    "/reports/dues/?export=csv",
    "/reports/monthly/", "/courses/", f"/courses/{co.pk}/edit/",
]
bad = []
for u in urls:
    r = c.get(M + u)
    if r.status_code not in (200, 302):
        bad.append((u, r.status_code))
    else:
        print(f"  {r.status_code}  {M}{u}")
r = c.get("/django-admin/")
print(f"  {r.status_code}  /django-admin/")

before = Student.objects.count()
c.post(M + "/students/new/", {
    "student_id": Student.next_student_id(), "name": "Test Student",
    "class_level": "10", "program": "", "batch": b.pk, "school": "",
    "phone": "", "guardian_name": "", "guardian_phone": "01700000000",
    "address": "", "joining_date": "2026-09-01", "admission_fee": "500",
    "status": "active", "note": "",
})
assert Student.objects.count() == before + 1, "student create failed"
new = Student.objects.get(name="Test Student")
print("student create OK ->", new.student_id)

c.post(M + "/enrollment/new/", {
    "student": new.pk, "month": month_start().isoformat(),
    "courses": [co.pk], "discount": "0", "note": "",
})
enr = MonthlyEnrollment.objects.get(student=new)
assert enr.fee_charged == co.monthly_fee
print("enrollment create OK -> charged", enr.fee_charged)

c.post(M + "/fees/collect/", {
    "student": new.pk, "category": "monthly_fee", "month": m,
    "amount": "200", "paid_on": "2026-09-10", "method": "bkash",
    "received_by": "Rakib", "note": "part",
})
enr.refresh_from_db()
assert enr.paid == 200 and enr.payment_status == "part"
print("payment OK -> paid", enr.paid, "due", enr.due, enr.payment_status_label)

c.post(M + "/enrollment/new/", {
    "student": new.pk, "month": month_start().isoformat(),
    "courses": [co.pk], "discount": "0", "note": "",
})
assert MonthlyEnrollment.objects.filter(student=new).count() == 1, "duplicate allowed!"
print("duplicate enrollment blocked OK")

nxt = add_months(month_start(), 1)
c.post(M + "/enrollment/carry-forward/", {
    "source": month_start().strftime("%Y-%m"), "target": nxt.strftime("%Y-%m")})
n_next = MonthlyEnrollment.objects.filter(month=nxt).count()
assert n_next > 0
print("carry forward OK ->", n_next, "rows in", nxt.strftime("%b %Y"))
c.post(M + "/enrollment/carry-forward/", {
    "source": month_start().strftime("%Y-%m"), "target": nxt.strftime("%Y-%m")})
assert MonthlyEnrollment.objects.filter(month=nxt).count() == n_next, "carry duplicated!"
print("carry forward is idempotent OK")

before_exp = Expense.objects.count()
c.post(M + "/teachers/pay/", {
    "teacher": t.pk, "month": month_start().isoformat(), "amount": "5000",
    "paid_on": "2026-09-28", "method": "cash", "note": ""})
assert Expense.objects.count() == before_exp + 1, "teacher payment did not create expense"
print("teacher payment -> expense OK")

anon = Client()
r = anon.get(M + "/students/", follow=True)
assert b"Log in" in r.content, "staff pages reachable without login!"
print("login required OK")

print()
print("FAILURES:", bad if bad else "none")
