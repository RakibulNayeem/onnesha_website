from django.contrib import admin

from .models import (
    Attendance, Batch, Course, Expense, MonthlyEnrollment, Payment,
    Program, Student, Subject, Teacher, TeacherPayment,
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name", "class_level", "batch", "status", "phone")
    list_filter = ("status", "class_level", "batch", "program")
    search_fields = ("student_id", "name", "phone", "guardian_phone")
    ordering = ("student_id",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("subject", "class_level", "program", "monthly_fee", "teacher", "is_active")
    list_filter = ("class_level", "program", "is_active")


@admin.register(MonthlyEnrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "month", "fee_charged", "discount")
    list_filter = ("month", "batch")
    search_fields = ("student__student_id", "student__name")
    filter_horizontal = ("courses",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("paid_on", "student", "category", "month", "amount", "method")
    list_filter = ("category", "method", "month")
    search_fields = ("student__student_id", "student__name")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("spent_on", "category", "description", "amount", "paid_to")
    list_filter = ("category", "method")


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("name", "pay_type", "fixed_monthly", "share_percent",
                    "show_on_website", "is_active")
    list_filter = ("show_on_website", "is_active")
    filter_horizontal = ("subjects",)
    fieldsets = (
        (None, {"fields": ("name", "phone", "subjects", "is_active", "note")}),
        ("Payment", {"fields": ("pay_type", "fixed_monthly", "share_percent",
                                "hourly_rate")}),
        ("Public website profile", {
            "fields": ("show_on_website", "display_order", "photo", "photo_url",
                       "designation_bn", "designation_en",
                       "qualification_bn", "qualification_en",
                       "bio_bn", "bio_en"),
        }),
    )


@admin.register(TeacherPayment)
class TeacherPaymentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "month", "amount", "paid_on")
    list_filter = ("month", "teacher")


admin.site.register([Program, Subject, Batch, Attendance])
admin.site.site_header = "Onnesha administration"
admin.site.site_title = "Onnesha"
