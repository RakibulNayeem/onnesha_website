"""Roles are Django groups. Superuser and the staff flag are Django built-ins.

  Student    - any signed-up account; no admin access
  Teacher    - writes questions (own only, always saved as drafts)
  Moderator  - reviews and approves everyone's questions
  Admin      - runs content, exams and non-admin users
  Superuser  - owner; also creates Admins
"""
from django.contrib.auth.models import Group, Permission

TEACHER, MODERATOR, ADMIN = "Teacher", "Moderator", "Admin"
LABELS = {"superuser": "সুপার অ্যাডমিন", ADMIN: "অ্যাডমিন", MODERATOR: "মডারেটর", TEACHER: "শিক্ষক", None: "শিক্ষার্থী"}


def role(user):
    """The user's highest role name: 'superuser', ADMIN, MODERATOR, TEACHER or None (student)."""
    if user.is_superuser:
        return "superuser"
    names = set(user.groups.values_list("name", flat=True))
    for r in (ADMIN, MODERATOR, TEACHER):
        if r in names:
            return r
    return None


def label(user):
    return LABELS[role(user)]


def can_approve(user):
    return user.is_superuser or user.has_perm("exams.approve_question")


def sync_roles():
    """Create or refresh the role groups. Safe to run repeatedly."""
    def perms(*codes, app="exams"):
        return list(Permission.objects.filter(content_type__app_label=app, codename__in=codes))

    view_tax = ["view_track", "view_subject", "view_chapter", "view_source"]
    teacher = perms("add_question", "change_question", "view_question", *view_tax)
    moderator = teacher + perms("delete_question", "approve_question", "change_chapter", "add_chapter")
    admin = list(Permission.objects.filter(content_type__app_label="exams")) + perms(
        "view_user", "add_user", "change_user", "view_group", app="auth")
    for name, p in ((TEACHER, teacher), (MODERATOR, moderator), (ADMIN, admin)):
        Group.objects.get_or_create(name=name)[0].permissions.set(p)
