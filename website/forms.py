from django import forms

from core.models import ClassLevel, Program, Subject

from .models import AdmissionApplication, ContactMessage

BS = "form-control"
BSS = "form-select"


class AdmissionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = [
            "name", "class_level", "program", "subjects", "school",
            "phone", "guardian_name", "guardian_phone", "address", "message",
        ]
        widgets = {
            "subjects": forms.CheckboxSelectMultiple(),
            "message": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].queryset = Program.objects.filter(is_active=True)
        self.fields["subjects"].queryset = Subject.objects.filter(is_active=True)
        self.fields["program"].required = False
        for name, field in self.fields.items():
            if name == "subjects":
                continue
            css = BSS if isinstance(field.widget, forms.Select) else BS
            field.widget.attrs.setdefault("class", css)

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 10:
            raise forms.ValidationError(
                "Please write a full mobile number. / \u09aa\u09c2\u09b0\u09cd\u09a3 \u09ae\u09cb\u09ac\u09be\u0987\u09b2 \u09a8\u09ae\u09cd\u09ac\u09b0 \u09b2\u09bf\u0996\u09c1\u09a8\u0964"
            )
        return phone


class ContactForm(forms.ModelForm):
    # simple bot trap: real people leave it empty
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = ContactMessage
        fields = ["name", "phone", "email", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "website":
                continue
            field.widget.attrs.setdefault("class", BS)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Spam detected.")
        return cleaned


class ResultLookupForm(forms.Form):
    student_id = forms.CharField(
        max_length=24,
        widget=forms.TextInput(attrs={"class": BS, "placeholder": "ONS-26-0001"}),
    )
