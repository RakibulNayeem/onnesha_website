from django import forms

from .i18n import tr_lazy as _
from .models import Chapter, Profile, Question, Source, Subject, Subscription

COUNTS = [(n, f"{n} questions") for n in (10, 20, 25, 30, 40, 50)]


def _bank():
    """Subjects that have at least one approved MCQ."""
    return Subject.objects.filter(
        questions__status=Question.APPROVED, questions__qtype=Question.MCQ
    ).select_related("track").distinct()


class ExamForm(forms.Form):
    subjects = forms.ModelMultipleChoiceField(queryset=Subject.objects.none(), label="Subjects")
    chapters = forms.ModelMultipleChoiceField(queryset=Chapter.objects.none(), required=False,
                                              label="Chapters (optional)")
    source = forms.ModelChoiceField(queryset=Source.objects.none(), required=False,
                                    empty_label=_("সব প্রশ্নব্যাংক"), label="প্রশ্নব্যাংক")
    count = forms.TypedChoiceField(choices=COUNTS, coerce=int, initial=25, label="Questions")
    minutes = forms.IntegerField(min_value=1, max_value=240, required=False,
                                 label="Minutes (default: 1 per question)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subjects = _bank()
        self.fields["subjects"].queryset = subjects
        self.fields["chapters"].queryset = Chapter.objects.filter(subject__in=subjects)
        self.fields["source"].queryset = Source.objects.filter(
            questions__status=Question.APPROVED, questions__qtype=Question.MCQ).distinct()


def username_taken(name, me):
    """True if another account already uses this username (case-insensitive)."""
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(username__iexact=name).exclude(pk=me.pk).exists()


class ProfileForm(forms.ModelForm):
    username = forms.CharField(label=_("ইউজারনেম"), max_length=150)
    first_name = forms.CharField(label=_("নাম"), max_length=150, required=False)
    last_name = forms.CharField(label=_("পদবি"), max_length=150, required=False)
    PERSONAL = ["username", "first_name", "last_name", "birth_date", "gender", "phone", "address"]
    ACADEMIC = ["institution", "level", "division", "batch_year"]
    batch_year = forms.TypedChoiceField(label=_("ব্যাচ (পরীক্ষার বছর)"), required=False, coerce=int, empty_value=None)
    field_order = PERSONAL + ACADEMIC

    class Meta:
        model = Profile
        fields = ["phone", "birth_date", "gender", "address", "institution", "level", "division", "batch_year"]
        labels = {"phone": _("ফোন"), "birth_date": _("জন্ম তারিখ"), "gender": _("ছাত্র/ছাত্রী"),
                  "address": _("ঠিকানা"), "institution": _("শিক্ষা প্রতিষ্ঠানের নাম"),
                  "level": _("কী নিয়ে চর্চা করতে চাও?"), "division": _("বিভাগ"), "batch_year": _("ব্যাচ (পরীক্ষার বছর)")}
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["first_name"].initial, self.fields["last_name"].initial = user.first_name, user.last_name
        self.fields["username"].initial = user.username
        self.fields["username"].validators = list(user._meta.get_field("username").validators)
        from datetime import date
        from .i18n import tr
        year = date.today().year
        years = set(range(year - 1, year + 9)) | ({self.instance.batch_year} if self.instance.batch_year else set())
        self.fields["batch_year"].choices = [("", tr("বাছাই করো"))] + [(y, y) for y in sorted(years)]
        for k in ("gender", "level", "division"):
            self.fields[k].choices = [("", tr("বাছাই করো"))] + [(v, tr(l)) for v, l in self.fields[k].choices if v]

    def clean_username(self):
        name = self.cleaned_data["username"].strip()
        if username_taken(name, self.user):
            raise forms.ValidationError(_("এই ইউজারনেম আগেই নেওয়া হয়েছে।"))
        return name

    def clean(self):
        d = super().clean()
        if d.get("level") and d["level"] not in ("ssc", "dakhil", "hsc", "alim"):
            d["division"] = ""            # classes 6-8 have no division
        return d

    def save(self, commit=True):
        obj = super().save(commit)
        u = self.user
        u.username, u.first_name, u.last_name = (self.cleaned_data["username"], self.cleaned_data["first_name"],
                                                  self.cleaned_data["last_name"])
        u.save(update_fields=["username", "first_name", "last_name"])
        return obj

    def personal(self):
        return [self[n] for n in self.PERSONAL]

    def academic(self):
        return [self[n] for n in self.ACADEMIC]


RECEIPT_TYPES = {b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg", b"%PDF-": "application/pdf"}
RECEIPT_MAX = 3 * 1024 * 1024


class PaymentForm(forms.ModelForm):
    proof = forms.FileField(label=_("পেমেন্টের স্ক্রিনশট বা রসিদ (PNG, JPG, PDF — সর্বোচ্চ ৩ MB)"),
                            widget=forms.ClearableFileInput(attrs={"accept": ".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"}))

    class Meta:
        model = Subscription
        fields = ["method", "sender_number", "txn_id"]
        labels = {"method": _("পেমেন্ট মাধ্যম"), "sender_number": _("যে নম্বর থেকে পাঠিয়েছ"),
                  "txn_id": _("ট্রানজ্যাকশন আইডি (ঐচ্ছিক)")}
    field_order = ["method", "sender_number", "txn_id", "proof"]

    def clean_txn_id(self):
        t = self.cleaned_data["txn_id"].strip().upper()
        if t and Subscription.objects.filter(txn_id=t).exists():
            raise forms.ValidationError(_("এই ট্রানজ্যাকশন আইডি আগেই জমা দেওয়া হয়েছে।"))
        return t

    def clean_proof(self):
        f = self.cleaned_data["proof"]
        if f.size > RECEIPT_MAX:
            raise forms.ValidationError(_("ফাইল ৩ MB-এর বেশি হতে পারবে না।"))
        head = f.read(8)
        f.seek(0)
        kind = next((t for sig, t in RECEIPT_TYPES.items() if head.startswith(sig)), None)   # trust the bytes, not the name
        if not kind:
            raise forms.ValidationError(_("শুধু PNG, JPG বা PDF ফাইল দেওয়া যাবে।"))
        f.detected_type = kind
        return f
