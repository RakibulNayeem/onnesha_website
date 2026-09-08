"""
Public website content for Onnesha.

Every piece of visible text exists twice: `_bn` (Bengali) and `_en` (English).
Templates pick one with the `bl` filter based on the visitor's chosen language,
and fall back to whichever field is filled in if the other is empty.

Images and files can either be uploaded OR given as an external URL. That
second option matters on serverless hosting (Vercel), where uploaded files do
not survive between requests - paste a Facebook, Drive or Imgur link instead.
"""
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from core.models import ClassLevel, Program, Student, Subject, Teacher


class BilingualMixin(models.Model):
    class Meta:
        abstract = True

    def pick(self, base, lang):
        bn = getattr(self, f"{base}_bn", "") or ""
        en = getattr(self, f"{base}_en", "") or ""
        if lang == "bn":
            return bn or en
        return en or bn


class SiteSettings(models.Model):
    """One row. Edit it in the admin to change the whole site."""

    hero_title_bn = models.CharField(max_length=200, default="\u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be")
    hero_title_en = models.CharField(max_length=200, default="Onnesha")
    hero_subtitle_bn = models.CharField(max_length=300, blank=True)
    hero_subtitle_en = models.CharField(max_length=300, blank=True)
    hero_image_url = models.URLField(blank=True)
    about_bn = models.TextField(blank=True)
    about_en = models.TextField(blank=True)
    address_bn = models.CharField(max_length=200, blank=True)
    address_en = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=60, blank=True)
    email = models.EmailField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    map_embed_url = models.URLField(
        blank=True, help_text="Google Maps 'Embed a map' src link."
    )
    established_year = models.CharField(max_length=8, blank=True)
    students_count = models.CharField(max_length=12, blank=True)
    teachers_count = models.CharField(max_length=12, blank=True)
    success_rate = models.CharField(max_length=12, blank=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class HeroSlide(BilingualMixin):
    """Banner slides for the carousel at the top of the home page."""

    title_bn = models.CharField(max_length=160, blank=True)
    title_en = models.CharField(max_length=160, blank=True)
    subtitle_bn = models.CharField(max_length=300, blank=True)
    subtitle_en = models.CharField(max_length=300, blank=True)
    image = models.FileField(upload_to="slides/", blank=True)
    image_url = models.URLField(
        blank=True,
        help_text="Use this instead of uploading when the site runs on Vercel.",
    )
    button_text_bn = models.CharField(max_length=60, blank=True)
    button_text_en = models.CharField(max_length=60, blank=True)
    button_url = models.CharField(
        max_length=200, blank=True,
        help_text="A path like /admission/ or a full https:// link.",
    )
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title_en or self.title_bn or f"Slide {self.pk}"

    @property
    def src(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class PublishedQuerySet(models.QuerySet):
    def live(self):
        return self.filter(is_published=True, published_at__lte=timezone.now())


class Notice(BilingualMixin):
    title_bn = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    body_bn = models.TextField(blank=True)
    body_en = models.TextField(blank=True)
    attachment = models.FileField(upload_to="notices/", blank=True)
    attachment_url = models.URLField(blank=True)
    is_pinned = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-is_pinned", "-published_at"]

    def __str__(self):
        return self.title_en or self.title_bn

    def get_absolute_url(self):
        return reverse("pub_notice_detail", args=[self.pk])

    @property
    def file_link(self):
        if self.attachment:
            return self.attachment.url
        return self.attachment_url or ""


class GalleryAlbum(BilingualMixin):
    title_bn = models.CharField(max_length=140, blank=True)
    title_en = models.CharField(max_length=140, blank=True)
    held_on = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-held_on", "-id"]

    def __str__(self):
        return self.title_en or self.title_bn


class GalleryImage(models.Model):
    album = models.ForeignKey(
        GalleryAlbum, on_delete=models.CASCADE, related_name="images",
        null=True, blank=True,
    )
    caption_bn = models.CharField(max_length=160, blank=True)
    caption_en = models.CharField(max_length=160, blank=True)
    image = models.FileField(upload_to="gallery/", blank=True)
    image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self):
        return self.caption_en or self.caption_bn or f"Image {self.pk}"

    @property
    def src(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class VideoLecture(BilingualMixin):
    title_bn = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    description_bn = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    youtube_url = models.URLField(help_text="Paste the normal YouTube link.")
    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, null=True, blank=True
    )
    class_level = models.CharField(
        max_length=2, choices=ClassLevel.choices, blank=True
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_short = models.BooleanField(
        default=False, help_text="Tick for a short / reel rather than a full lecture."
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title_en or self.title_bn

    @property
    def youtube_id(self):
        url = self.youtube_url or ""
        for marker in ("v=", "youtu.be/", "/shorts/", "/embed/"):
            if marker in url:
                tail = url.split(marker, 1)[1]
                return tail.split("&")[0].split("?")[0].split("/")[0]
        return ""

    @property
    def embed_url(self):
        vid = self.youtube_id
        return f"https://www.youtube.com/embed/{vid}" if vid else ""

    @property
    def thumbnail(self):
        vid = self.youtube_id
        return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg" if vid else ""


class DownloadCategory(models.TextChoices):
    ROUTINE = "routine", "Class routine"
    SYLLABUS = "syllabus", "Syllabus"
    SHEET = "sheet", "Lecture sheet"
    QUESTION = "question", "Question paper"
    FORM = "form", "Form"
    OTHER = "other", "Other"


class Download(BilingualMixin):
    title_bn = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    category = models.CharField(
        max_length=12, choices=DownloadCategory.choices,
        default=DownloadCategory.OTHER,
    )
    class_level = models.CharField(
        max_length=2, choices=ClassLevel.choices, blank=True
    )
    file = models.FileField(upload_to="downloads/", blank=True)
    file_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title_en or self.title_bn

    @property
    def link(self):
        if self.file:
            return self.file.url
        return self.file_url or ""


class BlogPost(BilingualMixin):
    title_bn = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt_bn = models.CharField(max_length=300, blank=True)
    excerpt_en = models.CharField(max_length=300, blank=True)
    body_bn = models.TextField(blank=True)
    body_en = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    cover = models.FileField(upload_to="blog/", blank=True)
    author = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title_en or self.title_bn

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title_en or self.title_bn or "post")[:180] or "post"
            slug, n = base, 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("pub_blog_detail", args=[self.slug])

    @property
    def cover_src(self):
        if self.cover:
            return self.cover.url
        return self.cover_url or ""


class Exam(BilingualMixin):
    name_bn = models.CharField(max_length=160, blank=True)
    name_en = models.CharField(max_length=160, blank=True)
    class_level = models.CharField(max_length=2, choices=ClassLevel.choices)
    program = models.ForeignKey(
        Program, on_delete=models.SET_NULL, null=True, blank=True
    )
    held_on = models.DateField(default=timezone.now)
    total_marks = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(
        default=False, help_text="Results are hidden from the site until this is ticked."
    )
    show_public_list = models.BooleanField(
        default=True,
        help_text="Show the merit list to everyone. Untick to allow only "
                  "private lookup by student ID.",
    )
    published_at = models.DateTimeField(default=timezone.now)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-held_on"]

    def __str__(self):
        return f"{self.name_en or self.name_bn} ({self.get_class_level_display()})"

    def get_absolute_url(self):
        return reverse("pub_result_detail", args=[self.pk])

    def rank_results(self):
        """Recompute positions, highest total first. Ties share a position."""
        rows = list(self.results.order_by("-obtained_marks"))
        last_marks, last_pos = None, 0
        for i, r in enumerate(rows, start=1):
            if r.obtained_marks != last_marks:
                last_pos = i
                last_marks = r.obtained_marks
            if r.position != last_pos:
                r.position = last_pos
                r.save(update_fields=["position"])
        return len(rows)


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="exam_results"
    )
    roll = models.CharField(max_length=20, blank=True)
    obtained_marks = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    position = models.PositiveIntegerField(default=0)
    remark = models.CharField(max_length=140, blank=True)

    class Meta:
        ordering = ["position", "-obtained_marks"]
        unique_together = [("exam", "student")]

    def __str__(self):
        return f"{self.student.name} - {self.obtained_marks}"

    @property
    def percentage(self):
        total = self.exam.total_marks or 0
        if not total:
            return 0
        return round(float(self.obtained_marks) / total * 100, 1)

    @property
    def grade(self):
        p = self.percentage
        for cut, g in ((80, "A+"), (70, "A"), (60, "A-"), (50, "B"),
                       (40, "C"), (33, "D")):
            if p >= cut:
                return g
        return "F"


class SubjectMark(models.Model):
    result = models.ForeignKey(
        ExamResult, on_delete=models.CASCADE, related_name="subject_marks"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    out_of = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["subject__name"]
        unique_together = [("result", "subject")]

    def __str__(self):
        return f"{self.subject} - {self.marks}"


class ApplicationStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    ADMITTED = "admitted", "Admitted"
    CLOSED = "closed", "Not proceeding"


class AdmissionApplication(models.Model):
    """Filled in by a guardian on the public site. Not a Student yet."""

    name = models.CharField(max_length=120)
    class_level = models.CharField(max_length=2, choices=ClassLevel.choices)
    program = models.ForeignKey(
        Program, on_delete=models.SET_NULL, null=True, blank=True
    )
    subjects = models.ManyToManyField(Subject, blank=True)
    school = models.CharField(max_length=140, blank=True)
    phone = models.CharField(max_length=24)
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_phone = models.CharField(max_length=24, blank=True)
    address = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=12, choices=ApplicationStatus.choices,
        default=ApplicationStatus.NEW,
    )
    staff_note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=24, blank=True)
    email = models.EmailField(blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.created_at:%d %b %Y}"
