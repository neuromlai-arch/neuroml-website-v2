from django import forms

from careers.models import JobApplication
from core.forms import HoneypotForm

TEXT_INPUT = "w-full rounded-lg border border-hairline bg-white px-4 py-3 text-sm text-ink-body placeholder:text-ink-muted"


class JobApplicationForm(HoneypotForm, forms.ModelForm):
    """Resume validation (PDF/DOC/DOCX, 5MB) already lives on the model
    field's validators — this form just surfaces those errors inline."""

    class Meta:
        model = JobApplication
        fields = ["full_name", "email", "phone", "resume", "portfolio_url", "cover_note"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "email": forms.EmailInput(attrs={"class": TEXT_INPUT}),
            "phone": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "portfolio_url": forms.URLInput(attrs={"class": TEXT_INPUT}),
            "cover_note": forms.Textarea(attrs={"class": TEXT_INPUT, "rows": 4}),
        }

    def __init__(self, *args, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.fields["phone"].required = False
        self.fields["portfolio_url"].required = False
        self.fields["cover_note"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.job = self.job
        if commit:
            instance.save()
        return instance
