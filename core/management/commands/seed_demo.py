"""Fill an empty database with a realistic Onnesha setup so you can click around."""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Attendance, Batch, Course, Expense, ExpenseCategory, MonthlyEnrollment,
    Payment, PaymentCategory, PaymentMethod, PayType, Program, Student,
    Subject, Teacher, TeacherPayment, add_months, month_start,
)

NAMES = [
    "Tasnim Akter", "Rafiul Islam", "Nusrat Jahan", "Sadman Sakib",
    "Mehjabin Chowdhury", "Arafat Hossain", "Sumaiya Islam", "Tanvir Ahmed",
    "Jannatul Ferdous", "Shakib Al Amin", "Farhana Yeasmin", "Rakibul Islam",
    "Anika Tabassum", "Mahmudul Hasan", "Sanjida Akter", "Nazmul Huda",
    "Ishrat Jahan", "Sabbir Rahman", "Maliha Noor", "Tahsin Alam",
]


class Command(BaseCommand):
    help = "Create demo programmes, courses, batches, students, fees and expenses."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=3)

    @transaction.atomic
    def handle(self, *args, **opts):
        if Student.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Database already has students - nothing seeded."))
            return

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "", "onnesha123")
            self.stdout.write(self.style.SUCCESS(
                "Created admin user  ->  username: admin   password: onnesha123"))

        academic = Program.objects.create(name="Academic", short_code="ACD")
        ssc = Program.objects.create(name="SSC Preparation", short_code="SSC")
        hsc = Program.objects.create(name="HSC Preparation", short_code="HSC")
        adm = Program.objects.create(name="Admission Test", short_code="ADM")

        subs = {n: Subject.objects.create(name=n) for n in [
            "Physics", "Chemistry", "Higher Math", "General Math",
            "Math", "Biology", "ICT", "English", "Bangla"]}

        t1 = Teacher.objects.create(name="Rakibul Naeem", phone="017XXXXXXXX",
                                    pay_type=PayType.FIXED,
                                    fixed_monthly=Decimal("12000"))
        t2 = Teacher.objects.create(name="Shafayet Azmir", phone="018XXXXXXXX",
                                    pay_type=PayType.PER_STUDENT,
                                    share_percent=Decimal("35"))
        t1.subjects.set([subs["Physics"], subs["Higher Math"]])
        t2.subjects.set([subs["Math"], subs["ICT"]])

        fee = {"8": 350, "9": 400, "10": 450, "11": 500, "12": 550, "AD": 700}
        offered = {
            "8": (academic, ["General Math", "English", "ICT"]),
            "9": (academic, ["Physics", "Chemistry", "Higher Math", "General Math", "ICT"]),
            "10": (ssc, ["Physics", "Chemistry", "Higher Math", "General Math", "ICT"]),
            "11": (academic, ["Physics", "Chemistry", "Math", "ICT"]),
            "12": (hsc, ["Physics", "Chemistry", "Math", "ICT", "Biology"]),
            "AD": (adm, ["Physics", "Chemistry", "Math", "English"]),
        }
        courses = {}
        for level, (prog, names) in offered.items():
            for n in names:
                teacher = t1 if n in ("Physics", "Higher Math") else t2
                courses[(level, n)] = Course.objects.create(
                    subject=subs[n], class_level=level, program=prog,
                    monthly_fee=Decimal(fee[level]), teacher=teacher,
                )

        batches = {}
        for level, (prog, _) in offered.items():
            label = dict(Course._meta.get_field("class_level").choices)[level]
            batches[level] = Batch.objects.create(
                name=f"{label} - {prog.short_code}", class_level=level,
                program=prog, schedule_note="Sat/Mon/Wed 4:00-6:00 PM",
            )

        levels = list(offered.keys())
        students = []
        for i, name in enumerate(NAMES):
            level = levels[i % len(levels)]
            s = Student.objects.create(
                name=name, class_level=level, batch=batches[level],
                program=offered[level][0],
                guardian_name="Guardian of " + name.split()[0],
                guardian_phone=f"018{random.randint(10000000, 99999999)}",
                joining_date=date.today() - timedelta(days=random.randint(10, 120)),
                admission_fee=Decimal("500"),
            )
            students.append(s)

        this_month = month_start()
        months = [add_months(this_month, -i) for i in range(opts["months"] - 1, -1, -1)]

        for m in months:
            for s in students:
                if random.random() < 0.12 and m != months[0]:
                    continue  # a few students skip a month
                pool = [c for (lvl, _), c in courses.items() if lvl == s.class_level]
                chosen = random.sample(pool, k=min(len(pool), random.randint(2, 4)))
                enr = MonthlyEnrollment.objects.create(
                    student=s, month=m, batch=s.batch,
                    discount=Decimal("0"),
                )
                enr.courses.set(chosen)
                enr.recalculate()

                roll = random.random()
                if roll < 0.6:
                    amount = enr.fee_charged
                elif roll < 0.85:
                    amount = (enr.fee_charged * Decimal("0.5")).quantize(Decimal("1"))
                else:
                    amount = Decimal("0")
                if amount > 0:
                    Payment.objects.create(
                        student=s, month=m, category=PaymentCategory.MONTHLY_FEE,
                        amount=amount,
                        paid_on=m + timedelta(days=random.randint(3, 20)),
                        method=random.choice(
                            [PaymentMethod.CASH, PaymentMethod.BKASH]),
                        received_by="Rakib",
                    )

            Expense.objects.create(
                spent_on=m, category=ExpenseCategory.RENT,
                description=f"Room rent - {m:%B %Y}", amount=Decimal("8000"),
                paid_to="Landlord", paid_by="Rakib")
            Expense.objects.create(
                spent_on=m + timedelta(days=2), category=ExpenseCategory.PRINTING,
                description="Sheets and model tests", amount=Decimal("1800"),
                paid_by="Shafayet")
            Expense.objects.create(
                spent_on=m + timedelta(days=4), category=ExpenseCategory.ELECTRICITY,
                description=f"Electricity - {m:%B %Y}", amount=Decimal("1200"),
                paid_by="Rakib")
            TeacherPayment.objects.create(
                teacher=t1, month=m, amount=t1.fixed_monthly,
                paid_on=m + timedelta(days=27))

        for s in students[:10]:
            for d in range(1, 15, 2):
                day = this_month + timedelta(days=d)
                if day <= date.today():
                    Attendance.objects.get_or_create(
                        student=s, batch=s.batch, on_date=day,
                        defaults={"present": random.random() > 0.15})

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(students)} students across {len(months)} months."))
