from django import forms

from .i18n import tr_lazy as _
from .models import Chapter, Profile, Question, Source, Subject

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


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label=_("নাম"), max_length=150, required=False)
    last_name = forms.CharField(label=_("পদবি"), max_length=150, required=False)
    PERSONAL = ["first_name", "last_name", "birth_date", "gender", "phone", "address"]
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
        from datetime import date
        from .i18n import tr
        year = date.today().year
        years = set(range(year - 1, year + 9)) | ({self.instance.batch_year} if self.instance.batch_year else set())
        self.fields["batch_year"].choices = [("", tr("বাছাই করো"))] + [(y, y) for y in sorted(years)]
        for k in ("gender", "level", "division"):
            self.fields[k].choices = [("", tr("বাছাই করো"))] + [(v, tr(l)) for v, l in self.fields[k].choices if v]

    def clean(self):
        d = super().clean()
        if d.get("level") and d["level"] not in ("ssc", "dakhil", "hsc", "alim"):
            d["division"] = ""            # classes 6-8 have no division
        return d

    def save(self, commit=True):
        obj = super().save(commit)
        self.user.first_name, self.user.last_name = self.cleaned_data["first_name"], self.cleaned_data["last_name"]
        self.user.save(update_fields=["first_name", "last_name"])
        return obj

    def personal(self):
        return [self[n] for n in self.PERSONAL]

    def academic(self):
        return [self[n] for n in self.ACADEMIC]
