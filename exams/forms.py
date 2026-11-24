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
    field_order = ["first_name", "last_name", "phone", "institution", "target"]

    class Meta:
        model = Profile
        fields = ["phone", "institution", "target"]
        labels = {"phone": _("ফোন"), "institution": _("স্কুল / কলেজ"), "target": _("যে পরীক্ষার প্রস্তুতি নিচ্ছ")}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["first_name"].initial, self.fields["last_name"].initial = user.first_name, user.last_name
        from .i18n import tr
        self.fields["target"].empty_label = tr("বাছাই করো")

    def save(self, commit=True):
        self.user.first_name, self.user.last_name = self.cleaned_data["first_name"], self.cleaned_data["last_name"]
        self.user.save(update_fields=["first_name", "last_name"])
        return super().save(commit)
