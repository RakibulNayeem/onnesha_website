from datetime import date

from django import forms

from .models import (
    Attendance, Batch, Course, Expense, MonthlyEnrollment, Payment,
    PaymentCategory, Program, Student, Subject, Teacher, TeacherPayment,
    month_start,
)

BS = "form-control"
BSS = "form-select"


class DateInput(forms.DateInput):
    input_type = "date"


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "student_id", "name", "class_level", "program", "batch", "school",
            "phone", "guardian_name", "guardian_phone", "address",
            "joining_date", "admission_fee", "status", "note",
        ]
        widgets = {
            "joining_date": DateInput(),
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("student_id"):
            self.initial["student_id"] = Student.next_student_id()
        self.fields["student_id"].help_text = (
            "Filled in for you. Type your own if you prefer \u2014 it only has to be unique."
        )
        for name, field in self.fields.items():
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)


class EnrollmentForm(forms.ModelForm):
    month = forms.DateField(widget=forms.HiddenInput())

    class Meta:
        model = MonthlyEnrollment
        fields = ["student", "month", "courses", "discount", "note"]
        widgets = {"courses": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.filter(
            is_active=True
        ).select_related("subject", "program")
        self.fields["student"].queryset = Student.objects.exclude(status="left")
        for name in ("student", "discount", "note"):
            css = BSS if name == "student" else BS
            self.fields[name].widget.attrs.setdefault("class", css)

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get("student")
        month = cleaned.get("month")
        if student and month:
            month = month_start(month)
            cleaned["month"] = month
            qs = MonthlyEnrollment.objects.filter(student=student, month=month)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"{student.name} is already enrolled for {month:%B %Y}. "
                    "Edit that row instead of adding a second one."
                )
        return cleaned


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "student", "category", "month", "amount", "paid_on",
            "method", "received_by", "note",
        ]
        widgets = {"paid_on": DateInput(), "month": forms.Select()}

    def __init__(self, *args, **kwargs):
        month_choices = kwargs.pop("month_choices", None)
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Student.objects.exclude(status="left")
        if month_choices:
            self.fields["month"] = forms.ChoiceField(
                choices=[("", "\u2014 not tied to a month \u2014")] + month_choices,
                required=False,
                label="Fee for which month",
            )
        for name, field in self.fields.items():
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)

    def clean_month(self):
        value = self.cleaned_data.get("month")
        if not value:
            return None
        if isinstance(value, str):
            from .utils import parse_month
            return parse_month(value)
        return month_start(value)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("category") == PaymentCategory.MONTHLY_FEE:
            if not cleaned.get("month"):
                self.add_error("month", "A monthly fee must say which month it is for.")
            if not cleaned.get("student"):
                self.add_error("student", "A monthly fee must belong to a student.")
        return cleaned


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            "spent_on", "category", "description", "amount", "batch",
            "paid_to", "method", "paid_by", "note",
        ]
        widgets = {"spent_on": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = [
            "name", "phone", "subjects", "pay_type", "fixed_monthly",
            "share_percent", "hourly_rate", "is_active", "note",
        ]
        widgets = {"subjects": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ("subjects", "is_active"):
                continue
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)


class TeacherPaymentForm(forms.ModelForm):
    class Meta:
        model = TeacherPayment
        fields = ["teacher", "month", "amount", "paid_on", "method", "note"]
        widgets = {"paid_on": DateInput(), "month": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["subject", "class_level", "program", "monthly_fee", "teacher", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "is_active":
                continue
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)
