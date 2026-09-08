from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("login/", auth_views.LoginView.as_view(
        template_name="core/login.html", redirect_authenticated_user=True
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("students/", views.student_list, name="student_list"),
    path("students/new/", views.student_form, name="student_create"),
    path("students/<int:pk>/edit/", views.student_form, name="student_edit"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),

    path("enrollment/", views.enrollment_month, name="enrollment_month"),
    path("enrollment/new/", views.enrollment_form, name="enrollment_create"),
    path("enrollment/<int:pk>/edit/", views.enrollment_form, name="enrollment_edit"),
    path("enrollment/<int:pk>/delete/", views.enrollment_delete, name="enrollment_delete"),
    path("enrollment/carry-forward/", views.enrollment_carry_forward,
         name="enrollment_carry_forward"),

    path("fees/collect/", views.payment_create, name="payment_create"),
    path("fees/", views.payment_list, name="payment_list"),
    path("fees/<int:pk>/receipt/", views.receipt, name="receipt"),
    path("fees/<int:pk>/delete/", views.payment_delete, name="payment_delete"),

    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),

    path("teachers/", views.teacher_list, name="teacher_list"),
    path("teachers/new/", views.teacher_form, name="teacher_create"),
    path("teachers/<int:pk>/edit/", views.teacher_form, name="teacher_edit"),
    path("teachers/pay/", views.teacher_pay, name="teacher_pay"),

    path("attendance/", views.attendance_mark, name="attendance_mark"),
    path("attendance/report/", views.attendance_report, name="attendance_report"),

    path("reports/dues/", views.due_report, name="due_report"),
    path("reports/monthly/", views.monthly_report, name="monthly_report"),

    path("courses/", views.course_list, name="course_list"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
]
