"""Every public form on the site, as a plain Django Form/ModelForm with
server-side validation. Each one mixes in HoneypotForm; rate limiting is
applied at the view layer (django-ratelimit), not here.
"""

from itertools import groupby

from django import forms

from core.forms import HoneypotForm
from insights.models import Handbook
from marketing.models import ContactSubmission, NewsletterSubscriber
from solutions.models import Service

TEXT_INPUT = "w-full rounded-lg border border-hairline bg-white px-4 py-3 text-sm text-ink-body placeholder:text-ink-muted"
TEXTAREA = TEXT_INPUT
SELECT = TEXT_INPUT


class ContactSubmissionBaseForm(HoneypotForm, forms.ModelForm):
    """Shared by the contact page, the demo/strategy-call CTA, and the lead
    popup — they differ only in which fields are shown and the `source`
    they're saved with, set by the view, not the form."""

    class Meta:
        model = ContactSubmission
        fields = [
            "first_name", "last_name", "email", "phone", "company",
            "service_interest", "project_stage", "budget_range", "message",
            "utm_source", "utm_medium", "utm_campaign",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "last_name": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "email": forms.EmailInput(attrs={"class": TEXT_INPUT}),
            "phone": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "company": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "service_interest": forms.Select(attrs={"class": SELECT}),
            "project_stage": forms.Select(attrs={"class": SELECT}),
            "budget_range": forms.Select(attrs={"class": SELECT}),
            "message": forms.Textarea(attrs={"class": TEXTAREA, "rows": 4}),
            "utm_source": forms.HiddenInput(),
            "utm_medium": forms.HiddenInput(),
            "utm_campaign": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "service_interest" in self.fields:
            field = self.fields["service_interest"]
            field.queryset = (
                Service.objects.live()
                .filter(show_in_form_dropdown=True)
                .select_related("cluster")
                .order_by("cluster__order", "order")
            )
            field.required = False
            # ModelChoiceField.clean() resolves by pk against the queryset above,
            # not against .choices — so overriding choices with optgroups here
            # only changes what's rendered, it can't break validation.
            field.choices = [("", "Select a service")] + [
                (cluster.name, [(service.pk, service.title) for service in services])
                for cluster, services in groupby(field.queryset, key=lambda s: s.cluster)
            ]
        for name in ("last_name", "phone", "company", "project_stage", "budget_range", "message"):
            if name in self.fields:
                self.fields[name].required = False


class ContactForm(ContactSubmissionBaseForm):
    """The full contact page form."""


class DemoForm(ContactSubmissionBaseForm):
    """Book-a-demo — same shape as ContactForm; only `source` differs,
    set by the view."""

    class Meta(ContactSubmissionBaseForm.Meta):
        fields = [
            "first_name", "last_name", "email", "phone", "company", "message",
            "utm_source", "utm_medium", "utm_campaign",
        ]


class PopupForm(HoneypotForm, forms.ModelForm):
    """The lead popup: fewer fields than the full contact form, per spec.
    `name` is split into first/last on save."""

    name = forms.CharField(max_length=160, widget=forms.TextInput(attrs={"class": TEXT_INPUT}))

    class Meta:
        model = ContactSubmission
        fields = ["email", "phone", "service_interest", "message", "utm_source", "utm_medium", "utm_campaign"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": TEXT_INPUT}),
            "phone": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "service_interest": forms.Select(attrs={"class": SELECT}),
            "message": forms.Textarea(attrs={"class": TEXTAREA, "rows": 3}),
            "utm_source": forms.HiddenInput(),
            "utm_medium": forms.HiddenInput(),
            "utm_campaign": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_interest"].queryset = (
            Service.objects.live().filter(show_in_form_dropdown=True)
        )
        self.fields["service_interest"].required = False
        self.fields["phone"].required = False
        self.fields["message"].required = False
        self.field_order = ["name", "email", "phone", "service_interest", "message"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        first, _, last = self.cleaned_data["name"].strip().partition(" ")
        instance.first_name = first
        instance.last_name = last
        if commit:
            instance.save()
        return instance


class HandbookGateForm(HoneypotForm, forms.ModelForm):
    """Gated handbook download: name + email only, `handbook` is set by the
    view from the URL, not user input."""

    class Meta:
        model = ContactSubmission
        fields = ["first_name", "last_name", "email", "company", "utm_source", "utm_medium", "utm_campaign"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "last_name": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "email": forms.EmailInput(attrs={"class": TEXT_INPUT}),
            "company": forms.TextInput(attrs={"class": TEXT_INPUT}),
            "utm_source": forms.HiddenInput(),
            "utm_medium": forms.HiddenInput(),
            "utm_campaign": forms.HiddenInput(),
        }

    def __init__(self, *args, handbook=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.handbook = handbook
        self.fields["last_name"].required = False
        self.fields["company"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.source = ContactSubmission.Source.HANDBOOK
        instance.handbook = self.handbook
        if commit:
            instance.save()
        return instance


class NewsletterForm(HoneypotForm, forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "w-full rounded-full border border-white/25 bg-transparent px-4 py-2 text-sm text-white placeholder:text-white/40",
                "placeholder": "you@company.com",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"]
        existing = NewsletterSubscriber.objects.filter(email__iexact=email).first()
        if existing and existing.confirmed:
            raise forms.ValidationError("That email is already subscribed.")
        return email
