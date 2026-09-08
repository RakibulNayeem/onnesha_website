from django.contrib import admin

from .models import (
    AdmissionApplication, BlogPost, ContactMessage, Download, Exam,
    ExamResult, GalleryAlbum, GalleryImage, HeroSlide, Notice, SiteSettings,
    SubjectMark, VideoLecture,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("__str__", "order", "is_published")
    list_editable = ("order", "is_published")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "published_at", "is_pinned", "is_published")
    list_filter = ("is_pinned", "is_published")
    search_fields = ("title_bn", "title_en", "body_bn", "body_en")


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 3


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ("__str__", "held_on", "is_published")
    inlines = [GalleryImageInline]


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "album", "order", "is_published")


@admin.register(VideoLecture)
class VideoLectureAdmin(admin.ModelAdmin):
    list_display = ("__str__", "subject", "class_level", "is_short", "is_published")
    list_filter = ("is_short", "is_published", "class_level", "subject")


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "category", "class_level", "is_published")
    list_filter = ("category", "class_level", "is_published")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "published_at", "is_published")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title_en",)}


class SubjectMarkInline(admin.TabularInline):
    model = SubjectMark
    extra = 4


class ExamResultInline(admin.TabularInline):
    model = ExamResult
    extra = 5
    fields = ("student", "roll", "obtained_marks", "remark")
    autocomplete_fields = ("student",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("__str__", "held_on", "total_marks", "is_published",
                    "show_public_list")
    list_filter = ("is_published", "class_level")
    inlines = [ExamResultInline]
    actions = ["recalculate_positions"]

    @admin.action(description="Recalculate merit positions")
    def recalculate_positions(self, request, queryset):
        total = sum(exam.rank_results() for exam in queryset)
        self.message_user(request, f"Ranked {total} result(s).")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.rank_results()


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "obtained_marks", "position")
    list_filter = ("exam",)
    search_fields = ("student__name", "student__student_id")
    inlines = [SubjectMarkInline]


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "class_level", "phone", "status", "created_at")
    list_filter = ("status", "class_level")
    search_fields = ("name", "phone", "guardian_phone")
    filter_horizontal = ("subjects",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_read", "created_at")
    list_filter = ("is_read",)
