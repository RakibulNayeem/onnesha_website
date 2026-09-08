import csv
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    CourseForm, EnrollmentForm, ExpenseForm, PaymentForm, StudentForm,
    TeacherForm, TeacherPaymentForm,
)
from .models import (
    Attendance, Batch, ClassLevel, Course, Expense, MonthlyEnrollment,
    Payment, PaymentCategory, Program, Student, StudentStatus, Subject,
    Teacher, TeacherPayment, add_months, month_start,
)
from .utils import month_options, months_between, parse_month, range_context

ZERO = Decimal("0")


def _sum(qs, field="amount"):
    return qs.aggregate(t=Sum(field))["t"] or ZERO


def _month_context(request, key="month"):
    month = parse_month(request.GET.get(key))
    return month, month_options(month)


# ============================================================ DASHBOARD
@login_required
def dashboard(request):
    month, options = _month_context(request)
    nxt = add_months(month, 1)

    payments = Payment.objects.filter(paid_on__gte=month, paid_on__lt=nxt)
    expenses = Expense.objects.filter(spent_on__gte=month, spent_on__lt=nxt)
    cash_in = _sum(payments)
    cash_out = _sum(expenses)

    enrollments = MonthlyEnrollment.objects.filter(month=month)
    charged = _sum(enrollments, "fee_charged")
    collected = _sum(
        Payment.objects.filter(month=month, category=PaymentCategory.MONTHLY_FEE)
    )
    due = charged - collected

    status_counts = {"paid": 0, "part": 0, "unpaid": 0, "free": 0}
    for e in enrollments.select_related("student"):
        status_counts[e.payment_status] += 1

    batch_rows = []
    for batch in Batch.objects.filter(is_active=True):
        b_enr = enrollments.filter(batch=batch)
        b_charged = _sum(b_enr, "fee_charged")
        b_collected = _sum(
            Payment.objects.filter(
                month=month, category=PaymentCategory.MONTHLY_FEE,
                student__enrollments__month=month,
                student__enrollments__batch=batch,
            ).distinct()
        )
        if b_enr.exists() or b_charged or b_collected:
            batch_rows.append({
                "batch": batch, "students": b_enr.count(),
                "charged": b_charged, "collected": b_collected,
                "due": b_charged - b_collected,
            })

    income_by_cat = (
        payments.values("category").annotate(total=Sum("amount")).order_by("-total")
    )
    for row in income_by_cat:
        row["label"] = dict(PaymentCategory.choices)[row["category"]]
    expense_by_cat = (
        expenses.values("category").annotate(total=Sum("amount")).order_by("-total")
    )
    from .models import ExpenseCategory
    for row in expense_by_cat:
        row["label"] = dict(ExpenseCategory.choices)[row["category"]]

    trend = []
    for i in range(-5, 1):
        m = add_months(month, i)
        m_next = add_months(m, 1)
        trend.append({
            "month": m,
            "income": _sum(Payment.objects.filter(paid_on__gte=m, paid_on__lt=m_next)),
            "expense": _sum(Expense.objects.filter(spent_on__gte=m, spent_on__lt=m_next)),
            "students": MonthlyEnrollment.objects.filter(month=m).count(),
        })
    for row in trend:
        row["profit"] = row["income"] - row["expense"]

    teacher_dues = []
    for t in Teacher.objects.filter(is_active=True):
        expected = t.expected_for_month(month)
        paid = t.paid_for_month(month)
        if expected or paid:
            teacher_dues.append({
                "teacher": t, "expected": expected, "paid": paid,
                "due": expected - paid,
            })

    context = {
        "month": month, "month_options": options,
        "month_value": month.strftime("%Y-%m"),
        "cash_in": cash_in, "cash_out": cash_out, "profit": cash_in - cash_out,
        "charged": charged, "collected": collected, "due": due,
        "collection_rate": (collected / charged * 100) if charged else ZERO,
        "enrolled": enrollments.count(),
        "courses_taken": enrollments.aggregate(t=Count("courses"))["t"] or 0,
        "active_students": Student.objects.filter(status=StudentStatus.ACTIVE).count(),
        "status_counts": status_counts,
        "batch_rows": batch_rows,
        "income_by_cat": income_by_cat, "expense_by_cat": expense_by_cat,
        "trend": trend, "teacher_dues": teacher_dues,
    }
    return render(request, "core/dashboard.html", context)


# ============================================================ STUDENTS
@login_required
def student_list(request):
    q = request.GET.get("q", "").strip()
    batch_id = request.GET.get("batch", "")
    class_level = request.GET.get("class_level", "")
    status = request.GET.get("status", "")

    students = Student.objects.select_related("batch", "program")
    if q:
        students = students.filter(
            Q(name__icontains=q) | Q(student_id__icontains=q)
            | Q(phone__icontains=q) | Q(guardian_phone__icontains=q)
        )
    if batch_id:
        students = students.filter(batch_id=batch_id)
    if class_level:
        students = students.filter(class_level=class_level)
    if status:
        students = students.filter(status=status)

    rows = [{"s": s, "due": s.total_due} for s in students[:500]]
    context = {
        "rows": rows, "q": q, "batches": Batch.objects.all(),
        "class_levels": ClassLevel.choices, "statuses": StudentStatus.choices,
        "batch_id": batch_id, "class_level": class_level, "status": status,
        "total": students.count(),
    }
    return render(request, "core/student_list.html", context)


@login_required
def student_form(request, pk=None):
    student = get_object_or_404(Student, pk=pk) if pk else None
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Saved {obj.name} ({obj.student_id}).")
            return redirect("student_detail", pk=obj.pk)
    else:
        form = StudentForm(instance=student)
    return render(
        request, "core/student_form.html",
        {"form": form, "student": student,
         "suggested_id": Student.next_student_id()},
    )


@login_required
def student_detail(request, pk):
    student = get_object_or_404(
        Student.objects.select_related("batch", "program"), pk=pk
    )
    enrollments = (
        student.enrollments.prefetch_related("courses__subject").order_by("-month")
    )
    rows = [{
        "e": e, "paid": e.paid, "due": e.due,
        "status": e.payment_status, "label": e.payment_status_label,
    } for e in enrollments]
    context = {
        "student": student, "rows": rows,
        "payments": student.payments.all()[:50],
        "charged": student.total_charged, "paid": student.total_paid,
        "due": student.total_due,
    }
    return render(request, "core/student_detail.html", context)


# ============================================================ ENROLLMENT
@login_required
def enrollment_month(request):
    month, options = _month_context(request)
    batch_id = request.GET.get("batch", "")
    status = request.GET.get("pay", "")
    q = request.GET.get("q", "").strip()

    enrollments = (
        MonthlyEnrollment.objects.filter(month=month)
        .select_related("student", "batch")
        .prefetch_related("courses__subject")
    )
    if batch_id:
        enrollments = enrollments.filter(batch_id=batch_id)
    if q:
        enrollments = enrollments.filter(
            Q(student__name__icontains=q) | Q(student__student_id__icontains=q)
        )

    rows = []
    totals = {"charged": ZERO, "paid": ZERO, "due": ZERO}
    for e in enrollments:
        st = e.payment_status
        if status and st != status:
            continue
        rows.append({"e": e, "paid": e.paid, "due": e.due,
                     "status": st, "label": e.payment_status_label})
        totals["charged"] += e.fee_charged
        totals["paid"] += e.paid
        totals["due"] += e.due

    enrolled_ids = set(enrollments.values_list("student_id", flat=True))
    not_enrolled = Student.objects.filter(status=StudentStatus.ACTIVE).exclude(
        pk__in=enrolled_ids
    )
    if batch_id:
        not_enrolled = not_enrolled.filter(batch_id=batch_id)

    prev_month = add_months(month, -1)
    context = {
        "month": month, "month_options": options,
        "month_value": month.strftime("%Y-%m"),
        "rows": rows, "totals": totals,
        "batches": Batch.objects.all(), "batch_id": batch_id,
        "pay": status, "q": q,
        "not_enrolled": not_enrolled,
        "prev_month": prev_month,
        "prev_count": MonthlyEnrollment.objects.filter(month=prev_month).count(),
    }
    return render(request, "core/enrollment_month.html", context)


@login_required
def enrollment_form(request, pk=None):
    enrollment = get_object_or_404(MonthlyEnrollment, pk=pk) if pk else None
    month = enrollment.month if enrollment else parse_month(request.GET.get("month"))
    initial = {"month": month}
    student_id = request.GET.get("student")
    if student_id and not enrollment:
        initial["student"] = student_id

    if request.method == "POST":
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            obj = form.save()
            obj.recalculate()
            messages.success(
                request, f"{obj.student.name} enrolled for {obj.month:%B %Y} "
                         f"\u2014 charged \u09f3{obj.fee_charged:,.0f}."
            )
            return redirect(
                f"{reverse('enrollment_month')}?month={obj.month:%Y-%m}"
            )
    else:
        form = EnrollmentForm(instance=enrollment, initial=initial)

    courses = Course.objects.filter(is_active=True).select_related(
        "subject", "program"
    )
    return render(request, "core/enrollment_form.html", {
        "form": form, "enrollment": enrollment, "month": month,
        "courses": courses,
    })


@login_required
def enrollment_delete(request, pk):
    e = get_object_or_404(MonthlyEnrollment, pk=pk)
    month = e.month
    if request.method == "POST":
        e.delete()
        messages.success(request, "Enrollment removed.")
    return redirect(f"{reverse('enrollment_month')}?month={month:%Y-%m}")


@login_required
def enrollment_carry_forward(request):
    """Copy every enrollment of one month into the next month."""
    if request.method != "POST":
        return redirect("enrollment_month")
    source = parse_month(request.POST.get("source"))
    target = parse_month(request.POST.get("target"))
    if source == target:
        messages.error(request, "Pick two different months.")
        return redirect(f"{reverse('enrollment_month')}?month={target:%Y-%m}")

    existing = set(
        MonthlyEnrollment.objects.filter(month=target).values_list(
            "student_id", flat=True
        )
    )
    created = skipped = 0
    for src in MonthlyEnrollment.objects.filter(month=source).prefetch_related("courses"):
        if src.student_id in existing:
            skipped += 1
            continue
        if src.student.status == StudentStatus.LEFT:
            skipped += 1
            continue
        new = MonthlyEnrollment.objects.create(
            student=src.student, month=target, batch=src.batch,
            discount=src.discount, note=src.note,
        )
        new.courses.set(src.courses.all())
        new.recalculate()
        created += 1

    if created:
        messages.success(
            request,
            f"Carried {created} student(s) from {source:%B %Y} into {target:%B %Y}."
            + (f" {skipped} skipped (already there or left)." if skipped else "")
        )
    else:
        messages.warning(
            request,
            f"Nothing to carry \u2014 {source:%B %Y} has no enrollments, "
            "or everyone is already in the target month."
        )
    return redirect(f"{reverse('enrollment_month')}?month={target:%Y-%m}")


# ============================================================ FEES
@login_required
def payment_create(request):
    month = parse_month(request.GET.get("month"))
    options = month_options(month)
    initial = {"month": month.strftime("%Y-%m"), "paid_on": date.today()}
    student_pk = request.GET.get("student")
    outstanding = None
    if student_pk:
        initial["student"] = student_pk
        enr = MonthlyEnrollment.objects.filter(
            student_id=student_pk, month=month
        ).first()
        if enr:
            outstanding = enr.due
            initial["amount"] = enr.due if enr.due > 0 else None

    if request.method == "POST":
        form = PaymentForm(request.POST, month_choices=options)
        if form.is_valid():
            p = form.save()
            messages.success(
                request,
                f"Received \u09f3{p.amount:,.0f}. Receipt {p.receipt_no}."
            )
            if "save_and_print" in request.POST:
                return redirect("receipt", pk=p.pk)
            return redirect(f"{reverse('payment_create')}?month={month:%Y-%m}")
    else:
        form = PaymentForm(initial=initial, month_choices=options)

    recent = Payment.objects.select_related("student")[:15]
    return render(request, "core/payment_form.html", {
        "form": form, "recent": recent, "month": month,
        "outstanding": outstanding,
    })


@login_required
def payment_list(request):
    rng = range_context(request.GET)
    scope = request.GET.get("scope", "paid_on")
    category = request.GET.get("category", "")
    q = request.GET.get("q", "").strip()

    payments = Payment.objects.select_related("student", "student__batch")
    if scope == "for_month":
        payments = payments.filter(
            month__gte=rng["start_month"], month__lt=rng["end_exclusive"]
        )
    else:
        payments = payments.filter(
            paid_on__gte=rng["start_month"], paid_on__lt=rng["end_exclusive"]
        )
    if category:
        payments = payments.filter(category=category)
    if q:
        payments = payments.filter(
            Q(student__name__icontains=q) | Q(student__student_id__icontains=q)
        )

    context = {
        "payments": payments[:500], "total": _sum(payments),
        "count": payments.count(),
        "categories": PaymentCategory.choices, "category": category,
        "scope": scope, "q": q,
    }
    context.update(rng)
    return render(request, "core/payment_list.html", context)


@login_required
def receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("student"), pk=pk)
    enrollment = None
    if payment.student and payment.month:
        enrollment = MonthlyEnrollment.objects.filter(
            student=payment.student, month=payment.month
        ).first()
    return render(request, "core/receipt.html",
                  {"p": payment, "enrollment": enrollment})


@login_required
def payment_delete(request, pk):
    p = get_object_or_404(Payment, pk=pk)
    if request.method == "POST":
        p.delete()
        messages.success(request, "Payment deleted.")
    return redirect("payment_list")


# ============================================================ EXPENSES
@login_required
def expense_list(request):
    rng = range_context(request.GET)
    expenses = Expense.objects.filter(
        spent_on__gte=rng["start_month"], spent_on__lt=rng["end_exclusive"]
    ).select_related("batch")
    category = request.GET.get("category", "")
    if category:
        expenses = expenses.filter(category=category)

    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            e = form.save()
            messages.success(request, f"Recorded \u09f3{e.amount:,.0f}.")
            return redirect(
                f"{reverse('expense_list')}"
                f"?from={rng['start_value']}&to={rng['end_value']}"
            )
    else:
        form = ExpenseForm(initial={"spent_on": date.today()})

    from .models import ExpenseCategory
    context = {
        "expenses": expenses, "total": _sum(expenses), "form": form,
        "categories": ExpenseCategory.choices, "category": category,
    }
    context.update(rng)
    return render(request, "core/expense_list.html", context)


@login_required
def expense_delete(request, pk):
    e = get_object_or_404(Expense, pk=pk)
    month = e.month
    if request.method == "POST":
        if hasattr(e, "teacher_payment") and e.teacher_payment:
            messages.error(
                request, "Delete this from the teacher payment page instead."
            )
        else:
            e.delete()
            messages.success(request, "Expense deleted.")
    params = request.POST if request.method == "POST" else request.GET
    start = parse_month(params.get("from"), month)
    end = parse_month(params.get("to"), month)
    return redirect(
        f"{reverse('expense_list')}?from={start:%Y-%m}&to={end:%Y-%m}"
    )


# ============================================================ TEACHERS
@login_required
def teacher_list(request):
    month, options = _month_context(request)
    rows = []
    for t in Teacher.objects.prefetch_related("subjects"):
        expected = t.expected_for_month(month)
        paid = t.paid_for_month(month)
        rows.append({"t": t, "expected": expected, "paid": paid,
                     "due": expected - paid})
    return render(request, "core/teacher_list.html", {
        "rows": rows, "month": month, "month_options": options,
        "month_value": month.strftime("%Y-%m"),
        "total_expected": sum(r["expected"] for r in rows) or ZERO,
        "total_paid": sum(r["paid"] for r in rows) or ZERO,
    })


@login_required
def teacher_form(request, pk=None):
    teacher = get_object_or_404(Teacher, pk=pk) if pk else None
    if request.method == "POST":
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, "Teacher saved.")
            return redirect("teacher_list")
    else:
        form = TeacherForm(instance=teacher)
    return render(request, "core/teacher_form.html",
                  {"form": form, "teacher": teacher})


@login_required
def teacher_pay(request):
    month = parse_month(request.GET.get("month"))
    initial = {"month": month, "paid_on": date.today()}
    teacher_pk = request.GET.get("teacher")
    if teacher_pk:
        initial["teacher"] = teacher_pk
        t = Teacher.objects.filter(pk=teacher_pk).first()
        if t:
            outstanding = t.expected_for_month(month) - t.paid_for_month(month)
            if outstanding > 0:
                initial["amount"] = outstanding

    if request.method == "POST":
        form = TeacherPaymentForm(request.POST)
        if form.is_valid():
            tp = form.save()
            messages.success(
                request,
                f"Paid \u09f3{tp.amount:,.0f} to {tp.teacher.name} "
                f"for {tp.month:%B %Y}. It is now in Expenses too."
            )
            return redirect(f"{reverse('teacher_list')}?month={tp.month:%Y-%m}")
    else:
        form = TeacherPaymentForm(initial=initial)

    return render(request, "core/teacher_pay.html", {
        "form": form, "month": month,
        "recent": TeacherPayment.objects.select_related("teacher")[:15],
    })


# ============================================================ ATTENDANCE
@login_required
def attendance_mark(request):
    batch_id = request.GET.get("batch") or request.POST.get("batch")
    on_date = request.GET.get("date") or request.POST.get("date") or str(date.today())
    batches = Batch.objects.filter(is_active=True)
    batch = Batch.objects.filter(pk=batch_id).first() if batch_id else None

    students = []
    if batch:
        students = Student.objects.filter(
            batch=batch, status=StudentStatus.ACTIVE
        ).order_by("student_id")

    if request.method == "POST" and batch:
        present_ids = set(request.POST.getlist("present"))
        for s in students:
            Attendance.objects.update_or_create(
                student=s, batch=batch, on_date=on_date,
                defaults={"present": str(s.pk) in present_ids},
            )
        messages.success(request, f"Attendance saved for {batch.name} on {on_date}.")
        return redirect(f"{reverse('attendance_mark')}?batch={batch.pk}&date={on_date}")

    existing = {}
    if batch:
        existing = {
            a.student_id: a.present
            for a in Attendance.objects.filter(batch=batch, on_date=on_date)
        }
    rows = [{"s": s, "present": existing.get(s.pk, True)} for s in students]
    return render(request, "core/attendance_mark.html", {
        "batches": batches, "batch": batch, "on_date": on_date, "rows": rows,
    })


@login_required
def attendance_report(request):
    rng = range_context(request.GET)
    batch_id = request.GET.get("batch", "")
    qs = Attendance.objects.filter(
        on_date__gte=rng["start_month"], on_date__lt=rng["end_exclusive"]
    )
    if batch_id:
        qs = qs.filter(batch_id=batch_id)

    rows = (
        qs.values("student__student_id", "student__name", "batch__name")
        .annotate(
            held=Count("id"),
            present=Count("id", filter=Q(present=True)),
        )
        .order_by("student__student_id")
    )
    for r in rows:
        r["percent"] = (r["present"] / r["held"] * 100) if r["held"] else 0
    context = {
        "rows": rows,
        "batches": Batch.objects.all(), "batch_id": batch_id,
    }
    context.update(rng)
    return render(request, "core/attendance_report.html", context)


# ============================================================ REPORTS
@login_required
def due_report(request):
    rng = range_context(request.GET)
    batch_id = request.GET.get("batch", "")
    scope = request.GET.get("scope", "all")
    # "month" is what the old one-month links called it.
    if scope == "month":
        scope = "range"

    enrollments = MonthlyEnrollment.objects.select_related(
        "student", "batch"
    ).order_by("student__student_id", "month")
    if scope == "range":
        enrollments = enrollments.filter(
            month__gte=rng["start_month"], month__lt=rng["end_exclusive"]
        )
    if batch_id:
        enrollments = enrollments.filter(batch_id=batch_id)

    rows = []
    total = ZERO
    for e in enrollments:
        d = e.due
        if d > 0:
            rows.append({"e": e, "due": d, "paid": e.paid})
            total += d

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="onnesha_dues.csv"'
        w = csv.writer(response)
        w.writerow(["Student ID", "Name", "Batch", "Month", "Charged", "Paid", "Due",
                    "Guardian phone"])
        for r in rows:
            e = r["e"]
            w.writerow([
                e.student.student_id, e.student.name,
                e.batch.name if e.batch else "", e.month.strftime("%b %Y"),
                e.fee_charged, r["paid"], r["due"], e.student.guardian_phone,
            ])
        return response

    context = {
        "rows": rows, "total": total, "scope": scope,
        "batches": Batch.objects.all(), "batch_id": batch_id,
    }
    context.update(rng)
    return render(request, "core/due_report.html", context)


@login_required
def monthly_report(request):
    rng = range_context(request.GET)
    start, nxt = rng["start_month"], rng["end_exclusive"]
    payments = Payment.objects.filter(paid_on__gte=start, paid_on__lt=nxt)
    expenses = Expense.objects.filter(spent_on__gte=start, spent_on__lt=nxt)
    enrollments = MonthlyEnrollment.objects.filter(
        month__gte=start, month__lt=nxt
    )

    from .models import ExpenseCategory
    income_rows = []
    for value, label in PaymentCategory.choices:
        income_rows.append({
            "label": label, "total": _sum(payments.filter(category=value))
        })
    expense_rows = []
    for value, label in ExpenseCategory.choices:
        t = _sum(expenses.filter(category=value))
        if t:
            expense_rows.append({"label": label, "total": t})

    course_rows = (
        Course.objects.filter(
            enrollments__month__gte=start, enrollments__month__lt=nxt
        )
        .annotate(students=Count("enrollments"))
        .order_by("-students")
    )
    for c in course_rows:
        c.expected = c.students * c.monthly_fee

    # Over a span, the single set of totals hides the shape of it.
    month_rows = []
    if rng["is_range"]:
        for m in months_between(start, rng["end_month"]):
            m_next = add_months(m, 1)
            m_in = _sum(Payment.objects.filter(paid_on__gte=m, paid_on__lt=m_next))
            m_out = _sum(Expense.objects.filter(spent_on__gte=m, spent_on__lt=m_next))
            month_rows.append({
                "month": m, "income": m_in, "expense": m_out,
                "profit": m_in - m_out,
                "students": MonthlyEnrollment.objects.filter(month=m).count(),
            })

    context = {
        "income_rows": income_rows, "expense_rows": expense_rows,
        "income_total": _sum(payments), "expense_total": _sum(expenses),
        "profit": _sum(payments) - _sum(expenses),
        "charged": _sum(enrollments, "fee_charged"),
        "collected": _sum(payments.filter(category=PaymentCategory.MONTHLY_FEE)),
        "enrolled": enrollments.values("student").distinct().count(),
        "course_rows": course_rows, "month_rows": month_rows,
    }
    context.update(rng)
    return render(request, "core/monthly_report.html", context)


# ============================================================ COURSES
@login_required
def course_list(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course saved.")
            return redirect("course_list")
    else:
        form = CourseForm()
    return render(request, "core/course_list.html", {
        "courses": Course.objects.select_related("subject", "program", "teacher"),
        "form": form,
    })


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated.")
            return redirect("course_list")
    else:
        form = CourseForm(instance=course)
    return render(request, "core/course_form.html",
                  {"form": form, "course": course})
