from django.conf import settings


def centre_info(request):
    return {
        "CENTRE_NAME": settings.CENTRE_NAME,
        "CENTRE_TAGLINE": settings.CENTRE_TAGLINE,
        "CENTRE_ADDRESS": settings.CENTRE_ADDRESS,
        "CENTRE_PHONE": settings.CENTRE_PHONE,
    }


NAV_MAP = {
    "dashboard": "dashboard",
    "student_list": "students", "student_create": "students",
    "student_edit": "students", "student_detail": "students",
    "enrollment_month": "enrollment", "enrollment_create": "enrollment",
    "enrollment_edit": "enrollment",
    "payment_create": "collect",
    "payment_list": "payments", "receipt": "payments",
    "expense_list": "expense",
    "teacher_list": "teachers", "teacher_create": "teachers",
    "teacher_edit": "teachers", "teacher_pay": "teachers",
    "attendance_mark": "attendance", "attendance_report": "attreport",
    "due_report": "dues", "monthly_report": "report",
    "course_list": "courses", "course_edit": "courses",
}


def nav(request):
    name = getattr(getattr(request, "resolver_match", None), "url_name", "")
    return {"nav": NAV_MAP.get(name, "")}
