from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group

from . import roles
from .models import Chapter, Profile, Question, Source, Subject, Track

admin.site.site_header = "অন্বেষা — প্রশ্ন প্যানেল"
admin.site.site_title = "অন্বেষা প্যানেল"
admin.site.index_title = "প্রশ্নব্যাংক ও ব্যবহারকারী পরিচালনা"


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "order"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubjectInline]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "track"]
    list_filter = ["track"]
    search_fields = ["name"]
    inlines = [ChapterInline]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "logo"]
    list_filter = ["kind"]
    search_fields = ["name"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Teachers see and edit only their own questions, always as drafts.
    Moderators and admins see everything and can approve."""
    list_display = ["short", "qtype", "subject", "chapter", "source", "status", "author", "issues"]
    list_filter = ["status", "qtype", "subject", "source", "author"]
    search_fields = ["text"]
    list_select_related = ["subject", "chapter", "source", "author"]
    autocomplete_fields = ["chapter"]
    actions = ["approve", "unapprove"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if roles.can_approve(request.user) else qs.filter(author=request.user)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        return ro if roles.can_approve(request.user) else ro + ["status", "author"]

    def get_list_filter(self, request):
        f = list(super().get_list_filter(request))
        return f if roles.can_approve(request.user) else [x for x in f if x != "author"]

    def get_actions(self, request):
        acts = super().get_actions(request)
        if not roles.can_approve(request.user):
            acts.pop("approve", None); acts.pop("unapprove", None)
        return acts

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        if not roles.can_approve(request.user):
            obj.status = Question.DRAFT        # any teacher edit goes back for review
        super().save_model(request, obj, form, change)

    @admin.display(description="question")
    def short(self, obj):
        return obj.text[:70]

    @admin.display(description="problems")
    def issues(self, obj):
        return ", ".join(obj.problems())

    @admin.action(description="Approve selected (skips incomplete ones)", permissions=["approve"])
    def approve(self, request, queryset):
        ok = [q for q in queryset if not q.problems()]
        Question.objects.filter(pk__in=[q.pk for q in ok]).update(status=Question.APPROVED)
        self.message_user(request, f"{len(ok)} approved.")
        if queryset.count() - len(ok):
            self.message_user(request, f"{queryset.count() - len(ok)} skipped - missing options, answer or parts.",
                              messages.WARNING)

    @admin.action(description="Send back to draft", permissions=["approve"])
    def unapprove(self, request, queryset):
        queryset.update(status=Question.DRAFT)

    def has_approve_permission(self, request):
        return roles.can_approve(request.user)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    search_fields = ["name", "subject__name"]  # required by autocomplete_fields
    list_display = ["name", "subject"]
    list_filter = ["subject"]


User = get_user_model()
admin.site.unregister(User)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admins can manage teachers, moderators and students, but not other admins or superusers."""
    inlines = [ProfileInline]
    list_display = ["username", "email", "role", "is_staff", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_active", "groups"]

    @admin.display(description="role")
    def role(self, obj):
        return roles.label(obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_superuser=False).exclude(groups__name=roles.ADMIN)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        return ro if request.user.is_superuser else ro + ["is_superuser", "user_permissions"]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups" and not request.user.is_superuser:
            kwargs["queryset"] = Group.objects.filter(name__in=[roles.TEACHER, roles.MODERATOR])
        return super().formfield_for_manytomany(db_field, request, **kwargs)
