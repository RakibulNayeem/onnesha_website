from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from exams import roles
from exams.models import Chapter, Question, Source, Subject, Track

User = get_user_model()
PARTS = range(1, 5)          # a creative question has up to four parts (ক খ গ ঘ)


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["qtype", "subject", "chapter", "source", "text", "option_a", "option_b", "option_c",
                  "option_d", "correct", "explanation", "refs", "reserved"]
        widgets = {"text": forms.Textarea(attrs={"rows": 5}), "explanation": forms.Textarea(attrs={"rows": 3}),
                   "correct": forms.RadioSelect}
        labels = {"qtype": "Type", "text": "Question (or CQ stem)", "refs": "Where it appeared",
                  "option_a": "ক  (a)", "option_b": "খ  (b)", "option_c": "গ  (c)", "option_d": "ঘ  (d)",
                  "correct": "Correct option", "source": "Question bank",
                  "reserved": "Hold back for exams"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chapter"].required = False
        self.fields["chapter"].queryset = Chapter.objects.select_related("subject")
        self.fields["source"].required = False
        self.fields["correct"].choices = [(k, k.upper()) for k in "abcd"]
        self.fields["correct"].required = False
        self.fields["refs"].help_text = ""
        self.fields["refs"].widget.attrs["placeholder"] = "e.g. ঢা. বো.'২৩; ব. বো.'২২"
        parts = (self.instance.parts if self.instance.pk else []) or []
        for i in PARTS:
            p = parts[i - 1] if i <= len(parts) else {}
            self.fields[f"p{i}_q"] = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), initial=p.get("q", ""))
            self.fields[f"p{i}_marks"] = forms.IntegerField(required=False, min_value=0, initial=p.get("marks", i))
            self.fields[f"p{i}_answer"] = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), initial=p.get("answer", ""))

    def part_rows(self):
        """[(number, question field, marks field, answer field), ...] for the template."""
        return [(i, self[f"p{i}_q"], self[f"p{i}_marks"], self[f"p{i}_answer"]) for i in PARTS]

    def clean(self):
        d = super().clean()
        subj, ch = d.get("subject"), d.get("chapter")
        if ch and subj and ch.subject_id != subj.id:
            self.add_error("chapter", "That chapter belongs to a different subject.")
        self.parts = []
        if d.get("qtype") in (Question.CQ, Question.SQ):
            for i in PARTS if d["qtype"] == Question.CQ else ():
                q = (d.get(f"p{i}_q") or "").strip()
                if q:
                    self.parts.append({"q": q, "marks": d.get(f"p{i}_marks") or 0, "answer": (d.get(f"p{i}_answer") or "").strip()})
            for k in ("option_a", "option_b", "option_c", "option_d", "correct"):
                d[k] = ""
        else:
            if d.get("correct") and not all((d.get(f"option_{x}") or "").strip() for x in "abcd"):
                self.add_error("correct", "Fill in all four options before choosing the correct one.")
        return d


class ContentForm(forms.ModelForm):
    """Tracks, subjects, chapters and banks share this; `Meta.model` is set per kind in views."""


def content_form(model, fields):
    meta = type("Meta", (), {"model": model, "fields": fields})
    return type(f"{model.__name__}Form", (ContentForm,), {"Meta": meta})


CONTENT = {
    "tracks": (Track, ["name", "slug", "kind", "order"], "Tracks", "A stream such as SSC, HSC, Admission or Job."),
    "subjects": (Subject, ["track", "name"], "Subjects", "A subject inside a track."),
    "chapters": (Chapter, ["subject", "name", "order"], "Chapters", "A chapter of a subject, in book order."),
    "banks": (Source, ["name", "kind", "year", "logo"], "Question banks", "A board and year, a university or an exam a question came from."),
}


class UserForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField()
    is_active = forms.BooleanField(required=False, initial=True, label="Active (can sign in)")
    password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False), label="Password")

    def __init__(self, *args, actor, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields["role"].choices = [("student" if k is None else k, v) for k, v in roles.assignable_roles(actor)]
        if instance:
            self.fields["password"].label = "New password (leave blank to keep the current one)"
            self.fields["username"].disabled = True
            # Always set: a disabled field takes its value from `initial`, even on a submitted form.
            for f in ("username", "email", "first_name", "last_name", "is_active"):
                self.initial[f] = getattr(instance, f)
            self.initial["role"] = roles.role(instance) or "student"
        else:
            self.fields["password"].required = True

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if not self.instance and User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("That username is taken.")
        return u

    def clean_password(self):
        pw = self.cleaned_data["password"]
        if pw:
            validate_password(pw)
        return pw

    def save(self):
        d = self.cleaned_data
        u = self.instance or User(username=d["username"])
        u.email, u.first_name, u.last_name, u.is_active = d["email"], d["first_name"], d["last_name"], d["is_active"]
        if d["password"]:
            u.set_password(d["password"])
        u.save()
        roles.apply_role(u, None if d["role"] == "student" else d["role"])
        return u
