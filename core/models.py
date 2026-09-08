"""
Data model for the Onnesha coaching-centre finance system.

The shape mirrors how a coaching centre actually runs:

    Student            -- registered once, ever
    MonthlyEnrollment  -- one row per student per month, listing the courses
                          taken that month; this is what creates the charge
    Payment            -- money received, linked to a student and a month
    Expense            -- money paid out
    Teacher / TeacherPayment -- what each teacher is owed and paid

A student can take three subjects in September, four in October and nothing
in November. Nothing is charged for a month with no enrollment row.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse

TK = "\u09f3"


def month_start(d=None):
    """Normalise any date to the first day of its month."""
    d = d or date.today()
    return date(d.year, d.month, 1)


def add_months(d, n):
    y, m = divmod((d.year * 12 + d.month - 1) + n, 12)
    return date(y, m + 1, 1)


class ClassLevel(models.TextChoices):
    C6 = "6", "Class 6"
    C7 = "7", "Class 7"
    C8 = "8", "Class 8"
    C9 = "9", "Class 9"
    C10 = "10", "Class 10"
    C11 = "11", "Class 11"
    C12 = "12", "Class 12"
    ADMISSION = "AD", "Admission Test"


class Program(models.Model):
    """Academic, SSC Preparation, HSC Preparation, Admission Test, and so on."""

    name = models.CharField(max_length=80, unique=True)
    name_bn = models.CharField(max_length=80, blank=True)
    short_code = models.CharField(max_length=12, blank=True)
    tagline_bn = models.CharField(max_length=200, blank=True)
    tagline_en = models.CharField(max_length=200, blank=True)
    description_bn = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40, blank=True,
        help_text="Bootstrap icon name, e.g. book, mortarboard, rocket-takeoff",
    )
    show_on_website = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Batch(models.Model):
    """A timetable group: 'Class 10 Science - Morning'."""

    name = models.CharField(max_length=80, unique=True)
    class_level = models.CharField(max_length=2, choices=ClassLevel.choices)
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="batches"
    )
    schedule_note = models.CharField(
        max_length=120, blank=True, help_text="e.g. Sat/Mon/Wed, 4:00-6:00 PM"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["class_level", "name"]
        verbose_name_plural = "batches"

    def __str__(self):
        return self.name


class Course(models.Model):
    """
    One sellable unit: a subject, at a class level, inside a program,
    with its own monthly fee. This is the price list.
    """

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="courses")
    class_level = models.CharField(max_length=2, choices=ClassLevel.choices)
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="courses")
    monthly_fee = models.DecimalField(
        max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    teacher = models.ForeignKey(
        "Teacher", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="courses",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["class_level", "program__name", "subject__name"]
        unique_together = [("subject", "class_level", "program")]

    def __str__(self):
        return f"{self.subject} - {self.get_class_level_display()} ({self.program})"

    @property
    def label(self):
        return f"{self.subject} \u00b7 {self.get_class_level_display()} \u00b7 {self.program} \u00b7 {TK}{self.monthly_fee:,.0f}"


class StudentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    HOLD = "hold", "On hold"
    LEFT = "left", "Left"


class Student(models.Model):
    student_id = models.CharField(
        max_length=24, unique=True, db_index=True,
        help_text="Generated automatically, but you can type your own.",
    )
    name = models.CharField(max_length=120)
    class_level = models.CharField(max_length=2, choices=ClassLevel.choices)
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, related_name="students", null=True, blank=True
    )
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="students", null=True, blank=True
    )
    school = models.CharField(max_length=140, blank=True)
    phone = models.CharField(max_length=24, blank=True)
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_phone = models.CharField(max_length=24, blank=True)
    address = models.CharField(max_length=200, blank=True)
    joining_date = models.DateField(default=date.today)
    admission_fee = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0")
    )
    status = models.CharField(
        max_length=10, choices=StudentStatus.choices, default=StudentStatus.ACTIVE
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student_id"]

    def __str__(self):
        return f"{self.student_id} - {self.name}"

    def get_absolute_url(self):
        return reverse("student_detail", args=[self.pk])

    # --- money -----------------------------------------------------------
    @property
    def total_charged(self):
        return self.enrollments.aggregate(t=Sum("fee_charged"))["t"] or Decimal("0")

    @property
    def total_paid(self):
        return self.payments.filter(category=PaymentCategory.MONTHLY_FEE).aggregate(
            t=Sum("amount")
        )["t"] or Decimal("0")

    @property
    def total_due(self):
        return self.total_charged - self.total_paid

    @staticmethod
    def next_student_id():
        """ONS-26-0001 style. Year comes from the current date."""
        prefix = getattr(settings, "STUDENT_ID_PREFIX", "ONS")
        yy = date.today().strftime("%y")
        stem = f"{prefix}-{yy}-"
        last = (
            Student.objects.filter(student_id__startswith=stem)
            .order_by("-student_id")
            .values_list("student_id", flat=True)
            .first()
        )
        n = 1
        if last:
            tail = last.rsplit("-", 1)[-1]
            if tail.isdigit():
                n = int(tail) + 1
        return f"{stem}{n:04d}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self.next_student_id()
        super().save(*args, **kwargs)


class MonthlyEnrollment(models.Model):
    """One row per student per month. No row = not studying that month."""

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="enrollments"
    )
    month = models.DateField(help_text="Always stored as the 1st of the month")
    courses = models.ManyToManyField(Course, related_name="enrollments", blank=True)
    batch = models.ForeignKey(
        Batch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enrollments",
    )
    discount = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0"),
        help_text="Taka off the monthly fee (waiver, sibling discount).",
    )
    fee_charged = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0"),
        help_text="Recalculated from the courses each time you save.",
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-month", "student__student_id"]
        unique_together = [("student", "month")]

    def __str__(self):
        return f"{self.student.student_id} \u00b7 {self.month:%b %Y}"

    def recalculate(self, commit=True):
        gross = self.courses.aggregate(t=Sum("monthly_fee"))["t"] or Decimal("0")
        self.fee_charged = max(Decimal("0"), gross - (self.discount or Decimal("0")))
        if commit:
            super().save(update_fields=["fee_charged"])
        return self.fee_charged

    def save(self, *args, **kwargs):
        self.month = month_start(self.month)
        if not self.batch_id and self.student_id:
            self.batch = self.student.batch
        super().save(*args, **kwargs)

    @property
    def course_count(self):
        return self.courses.count()

    @property
    def paid(self):
        return self.student.payments.filter(
            month=self.month, category=PaymentCategory.MONTHLY_FEE
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

    @property
    def due(self):
        return self.fee_charged - self.paid

    @property
    def payment_status(self):
        if self.fee_charged <= 0:
            return "free"
        if self.paid <= 0:
            return "unpaid"
        if self.due <= 0:
            return "paid"
        return "part"

    @property
    def payment_status_label(self):
        return {
            "free": "No fee", "unpaid": "Unpaid",
            "paid": "Paid", "part": "Part paid",
        }[self.payment_status]


class PaymentCategory(models.TextChoices):
    MONTHLY_FEE = "monthly_fee", "Monthly fee"
    ADMISSION = "admission", "Admission fee"
    EXAM = "exam", "Exam / model test fee"
    MATERIAL = "material", "Sheet / notes"
    OTHER = "other", "Other income"


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    BKASH = "bkash", "bKash"
    NAGAD = "nagad", "Nagad"
    ROCKET = "rocket", "Rocket"
    BANK = "bank", "Bank transfer"


class Payment(models.Model):
    """Money received. A monthly fee is always tagged with the month it is for."""

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="payments",
        null=True, blank=True,
    )
    month = models.DateField(
        null=True, blank=True,
        help_text="Which month this fee is FOR (not necessarily when it was paid).",
    )
    category = models.CharField(
        max_length=20, choices=PaymentCategory.choices,
        default=PaymentCategory.MONTHLY_FEE,
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    paid_on = models.DateField(default=date.today)
    method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    received_by = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-id"]

    def __str__(self):
        who = self.student.name if self.student else "-"
        return f"{TK}{self.amount:,.0f} \u00b7 {who} \u00b7 {self.get_category_display()}"

    def save(self, *args, **kwargs):
        if self.month:
            self.month = month_start(self.month)
        super().save(*args, **kwargs)

    @property
    def receipt_no(self):
        return f"R-{self.pk:06d}"


class ExpenseCategory(models.TextChoices):
    RENT = "rent", "House rent"
    TEACHER = "teacher", "Teacher payment"
    STAFF = "staff", "Staff salary"
    ELECTRICITY = "electricity", "Electricity bill"
    INTERNET = "internet", "Internet bill"
    PRINTING = "printing", "Photocopy & printing"
    STATIONERY = "stationery", "Stationery"
    FURNITURE = "furniture", "Furniture & equipment"
    MARKETING = "marketing", "Marketing & publicity"
    TRANSPORT = "transport", "Transport"
    REFRESHMENT = "refreshment", "Refreshment"
    REPAIR = "repair", "Repair & maintenance"
    CHARGE = "charge", "Bank / bKash charge"
    OTHER = "other", "Other expense"


class Expense(models.Model):
    spent_on = models.DateField(default=date.today)
    category = models.CharField(max_length=20, choices=ExpenseCategory.choices)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    batch = models.ForeignKey(
        Batch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="expenses", help_text="Only if the cost belongs to one batch.",
    )
    paid_to = models.CharField(max_length=120, blank=True)
    method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    paid_by = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-spent_on", "-id"]

    def __str__(self):
        return f"{TK}{self.amount:,.0f} \u00b7 {self.get_category_display()}"

    @property
    def month(self):
        return month_start(self.spent_on)


class PayType(models.TextChoices):
    FIXED = "fixed", "Fixed monthly amount"
    PER_STUDENT = "per_student", "Share of the fees collected"
    HOURLY = "hourly", "Per class / hourly"


class Teacher(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=24, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="teachers")
    pay_type = models.CharField(
        max_length=12, choices=PayType.choices, default=PayType.FIXED
    )
    fixed_monthly = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0"),
        help_text="Used when pay type is a fixed monthly amount.",
    )
    share_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        help_text="Percent of the fee collected on that teacher's courses.",
    )
    hourly_rate = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0")
    )
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)

    # --- shown on the public website ---
    show_on_website = models.BooleanField(default=False)
    designation_bn = models.CharField(max_length=120, blank=True)
    designation_en = models.CharField(max_length=120, blank=True)
    qualification_bn = models.CharField(max_length=200, blank=True)
    qualification_en = models.CharField(max_length=200, blank=True)
    bio_bn = models.TextField(blank=True)
    bio_en = models.TextField(blank=True)
    photo = models.FileField(upload_to="teachers/", blank=True)
    photo_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    @property
    def photo_src(self):
        if self.photo:
            return self.photo.url
        return self.photo_url or ""

    def pick(self, base, lang):
        bn = getattr(self, f"{base}_bn", "") or ""
        en = getattr(self, f"{base}_en", "") or ""
        return (bn or en) if lang == "bn" else (en or bn)

    def expected_for_month(self, month):
        """What this teacher should be paid for a given month."""
        month = month_start(month)
        if self.pay_type == PayType.FIXED:
            return self.fixed_monthly
        if self.pay_type == PayType.PER_STUDENT:
            collected = Payment.objects.filter(
                month=month, category=PaymentCategory.MONTHLY_FEE,
                student__enrollments__month=month,
                student__enrollments__courses__teacher=self,
            ).distinct().aggregate(t=Sum("amount"))["t"] or Decimal("0")
            return (collected * self.share_percent / Decimal("100")).quantize(
                Decimal("0.01")
            )
        return Decimal("0")  # hourly is entered by hand

    def paid_for_month(self, month):
        month = month_start(month)
        return self.payments.filter(month=month).aggregate(t=Sum("amount"))[
            "t"
        ] or Decimal("0")


class TeacherPayment(models.Model):
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="payments"
    )
    month = models.DateField(help_text="Which month's work this pays for")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    paid_on = models.DateField(default=date.today)
    method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    note = models.CharField(max_length=200, blank=True)
    expense = models.OneToOneField(
        Expense, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="teacher_payment",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-id"]

    def __str__(self):
        return f"{self.teacher} \u00b7 {self.month:%b %Y} \u00b7 {TK}{self.amount:,.0f}"

    def save(self, *args, **kwargs):
        self.month = month_start(self.month)
        super().save(*args, **kwargs)
        # keep the books honest: every teacher payment is also an expense
        if self.expense_id:
            exp = self.expense
            exp.spent_on = self.paid_on
            exp.amount = self.amount
            exp.method = self.method
            exp.description = f"{self.teacher.name} \u2014 {self.month:%b %Y}"
            exp.save()
        else:
            exp = Expense.objects.create(
                spent_on=self.paid_on,
                category=ExpenseCategory.TEACHER,
                description=f"{self.teacher.name} \u2014 {self.month:%b %Y}",
                amount=self.amount,
                paid_to=self.teacher.name,
                method=self.method,
                note=self.note,
            )
            TeacherPayment.objects.filter(pk=self.pk).update(expense=exp)
            self.expense = exp

    def delete(self, *args, **kwargs):
        exp = self.expense
        super().delete(*args, **kwargs)
        if exp:
            exp.delete()


class Attendance(models.Model):
    """Daily presence, entered batch by batch."""

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendance"
    )
    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name="attendance"
    )
    on_date = models.DateField(default=date.today)
    present = models.BooleanField(default=True)

    class Meta:
        ordering = ["-on_date"]
        unique_together = [("student", "batch", "on_date")]

    def __str__(self):
        mark = "P" if self.present else "A"
        return f"{self.on_date} \u00b7 {self.student.student_id} \u00b7 {mark}"
