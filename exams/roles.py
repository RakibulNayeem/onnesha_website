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
    from .i18n import tr
    return tr(LABELS[role(user)])


def can_approve(user):
    return user.is_superuser or user.has_perm("exams.approve_question")


# ---- the admin panel (/panel/) ---------------------------------------------------------------
RANK = {None: 0, TEACHER: 1, MODERATOR: 2, ADMIN: 3, "superuser": 4}
ROLE_CHOICES = [(None, "Student"), (TEACHER, "Teacher"), (MODERATOR, "Moderator"), (ADMIN, "Admin"), ("superuser", "Superuser")]


def rank(user):
    return RANK[role(user)]


def can_use_panel(user):
    """Anyone with a staff role (Teacher and above)."""
    return user.is_authenticated and user.is_active and user.is_staff and rank(user) >= 1


def can_write_questions(user):
    return can_use_panel(user)


def can_manage_content(user):
    """Tracks, subjects, chapters and question banks."""
    return can_use_panel(user) and rank(user) >= RANK[ADMIN]


def can_manage_users(user):
    return can_use_panel(user) and rank(user) >= RANK[ADMIN]


def assignable_roles(actor):
    """Roles the actor may give: Admins up to Moderator, superusers anything."""
    top = 4 if actor.is_superuser else RANK[ADMIN] - 1
    return [(k, v) for k, v in ROLE_CHOICES if RANK[k] <= top]


def can_manage_user(actor, target):
    """Superusers manage everyone; Admins only people below Admin; nobody edits their own role here."""
    if actor.pk == target.pk:
        return False
    return actor.is_superuser or rank(target) < RANK[ADMIN]


def apply_role(user, new_role):
    """Make `user` hold exactly one role: groups + staff flag + superuser flag."""
    for g in Group.objects.filter(name__in=(TEACHER, MODERATOR, ADMIN)):
        user.groups.remove(g)
    if new_role == "superuser":
        user.is_superuser = user.is_staff = True
    else:
        user.is_superuser = False
        user.is_staff = new_role is not None
        if new_role:
            user.groups.add(Group.objects.get(name=new_role))
    user.save(update_fields=["is_superuser", "is_staff"])


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
