from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

OPTION_KEYS = ("a", "b", "c", "d")


class Track(models.Model):
    """A stream a student prepares for: SSC, HSC, University admission, BCS..."""
    KINDS = [("academic", "একাডেমিক"), ("admission", "ভর্তি"), ("job", "চাকরি")]
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=10, choices=KINDS, default="academic")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Subject(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["track__order", "name"]
        unique_together = [("track", "name")]

    def __str__(self):
        return f"{self.name} ({self.track.name})"


class Chapter(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="chapters")
    name = models.CharField(max_length=150)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["subject", "order", "name"]
        unique_together = [("subject", "name")]

    def __str__(self):
        return f"{self.subject.name} - {self.name}"


class Source(models.Model):
    """Where a question came from: 'Dhaka University 2022-23', 'Dhaka Board 2023'."""
    KINDS = [("university", "বিশ্ববিদ্যালয়"), ("board", "বোর্ড"), ("job", "চাকরি"), ("other", "অন্যান্য")]
    name = models.CharField(max_length=150, unique=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="university", db_index=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Exam year, for boards and past papers.")
    logo = models.CharField(
        max_length=120, blank=True,
        help_text="File name inside static/img/logos/ (e.g. buet.png). Leave blank for a letter badge.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Question(models.Model):
    MCQ, CQ, SQ = "mcq", "cq", "sq"
    TYPES = [(MCQ, "MCQ"), (CQ, "CQ"), (SQ, "SQ")]
    DRAFT, APPROVED = "draft", "approved"
    STATUSES = [(DRAFT, "Draft - needs review"), (APPROVED, "Approved")]

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="questions")
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="questions")
    source = models.ForeignKey(Source, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="questions")
    qtype = models.CharField("type", max_length=3, choices=TYPES, default=MCQ)
    text = models.TextField("question / CQ stem")  # SQ: the question; its solution goes in `explanation`
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct = models.CharField(max_length=1, blank=True,
                               choices=[(k, k.upper()) for k in OPTION_KEYS])
    explanation = models.TextField(blank=True)
    refs = models.CharField("exam references", max_length=200, blank=True,
                            help_text="Where it appeared, as printed in the book, e.g. ঢা. বো.'২৩; ব. বো.'২২")
    # CQ only: [{"q": "...", "marks": 1, "answer": "..."}, ...]
    parts = models.JSONField(default=list, blank=True)
    reserved = models.BooleanField(
        default=False, db_index=True,
        help_text="Held back for self-test exams: not shown in the question bank, practice or CQ pages.")
    status = models.CharField(max_length=10, choices=STATUSES, default=DRAFT, db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="questions")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        permissions = [("approve_question", "Can approve (publish) questions")]

    def __str__(self):
        return self.text[:80]

    @property
    def options(self):
        return [(k, getattr(self, f"option_{k}")) for k in OPTION_KEYS]

    def problems(self):
        """Reasons this question is not fit to show students (empty = ok)."""
        out = []
        if self.qtype == self.MCQ:
            if not all(v.strip() for _, v in self.options):
                out.append("needs four options")
            if self.correct not in OPTION_KEYS:
                out.append("needs a correct answer")
        elif self.qtype == self.CQ and not self.parts:
            out.append("needs at least one part")
        return out

    def clean(self):
        if self.status == self.APPROVED and self.problems():
            raise ValidationError("Cannot approve: " + ", ".join(self.problems()))
        if self.chapter_id and self.subject_id and self.chapter.subject_id != self.subject_id:
            raise ValidationError("Chapter does not belong to that subject.")


class Exam(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="exams")
    title = models.CharField(max_length=200)
    duration_minutes = models.PositiveSmallIntegerField()
    negative = models.FloatField(default=0)  # marks lost per wrong answer
    created = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    correct = models.PositiveSmallIntegerField(default=0)
    wrong = models.PositiveSmallIntegerField(default=0)
    skipped = models.PositiveSmallIntegerField(default=0)
    score = models.FloatField(default=0)

    class Meta:
        ordering = ["-created"]

    @property
    def deadline(self):
        return self.created + timezone.timedelta(minutes=self.duration_minutes)

    @property
    def total(self):
        return self.correct + self.wrong + self.skipped

    @property
    def percent(self):
        return round(100 * self.correct / self.total) if self.total else 0

    def submit(self, answers):
        """Grade `answers` ({question_id: 'a'..'d'}) and close the exam."""
        rows = list(self.items.select_related("question"))
        for row in rows:
            row.chosen = answers.get(row.question_id, "")
            row.is_correct = (row.chosen == row.question.correct) if row.chosen else None
        ExamQuestion.objects.bulk_update(rows, ["chosen", "is_correct"])
        self.correct = sum(r.is_correct is True for r in rows)
        self.wrong = sum(r.is_correct is False for r in rows)
        self.skipped = len(rows) - self.correct - self.wrong
        self.score = self.correct - self.negative * self.wrong
        self.submitted_at = timezone.now()
        self.save()


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField()
    chosen = models.CharField(max_length=1, blank=True)
    is_correct = models.BooleanField(null=True)

    class Meta:
        ordering = ["order"]


class Profile(models.Model):
    """Extra account details. The role itself comes from the user's group (see roles.py)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    institution = models.CharField("school / college", max_length=120, blank=True)
    target = models.ForeignKey(Track, null=True, blank=True, on_delete=models.SET_NULL,
                               verbose_name="preparing for")
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, blank=True, choices=[("m", "ছাত্র"), ("f", "ছাত্রী"), ("o", "অন্যান্য")])
    address = models.CharField(max_length=200, blank=True)
    # What the student is studying for. It decides which bank tabs they see (see bank_tabs).
    LEVELS = [("c6", "ক্লাস ৬"), ("c7", "ক্লাস ৭"), ("c8", "ক্লাস ৮"), ("ssc", "এসএসসি"),
              ("dakhil", "দাখিল"), ("hsc", "এইচএসসি / অ্যাডমিশন"), ("alim", "আলিম")]
    DIVISIONS = [("science", "বিজ্ঞান"), ("humanities", "মানবিক"), ("commerce", "ব্যবসায় শিক্ষা")]
    level = models.CharField(max_length=6, blank=True, choices=LEVELS)
    division = models.CharField(max_length=10, blank=True, choices=DIVISIONS)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)

    @property
    def uses_division(self):
        return self.level in ("ssc", "dakhil", "hsc", "alim")

    @property
    def bank_tabs(self):
        """Bank tabs this student sees: university/job institutions only matter after school."""
        return ("subject", "board", "institution") if self.level in ("", "hsc") else ("subject", "board")

    def __str__(self):
        return f"Profile of {self.user}"



class Subscription(models.Model):
    """A Premium purchase. Students pay by mobile banking and submit the transaction id;
    an admin approves it, which starts the year (see plans.py)."""
    METHODS = [("bkash", "bKash"), ("nagad", "Nagad"), ("rocket", "Rocket")]
    PENDING, ACTIVE, REJECTED = "pending", "active", "rejected"
    STATUSES = [(PENDING, "Waiting for approval"), (ACTIVE, "Active"), (REJECTED, "Rejected")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    method = models.CharField(max_length=10, choices=METHODS)
    sender_number = models.CharField(max_length=20)
    txn_id = models.CharField("transaction id", max_length=40, blank=True)
    amount = models.PositiveIntegerField(default=199)
    status = models.CharField(max_length=10, choices=STATUSES, default=PENDING, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        constraints = [models.UniqueConstraint(fields=["txn_id"], condition=~models.Q(txn_id=""),
                                               name="unique_txn_when_given")]

    def __str__(self):
        return f"{self.user} - {self.get_status_display()} ({self.txn_id or 'no id'})"


class PaymentProof(models.Model):
    """The receipt screenshot or PDF for a payment. Kept in the database because the web host's disk
    is temporary; separate from Subscription so lists of payments never load the file bytes."""
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="proof")
    data = models.BinaryField()
    content_type = models.CharField(max_length=30)
    filename = models.CharField(max_length=120, blank=True)


class Friendship(models.Model):
    """A friend request (pending) that becomes a friendship once the other student accepts."""
    PENDING, ACCEPTED = "pending", "accepted"
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=10, default=PENDING, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["from_user", "to_user"], name="one_request_per_pair"),
                       models.CheckConstraint(check=~models.Q(from_user=models.F("to_user")), name="no_self_friend")]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"
