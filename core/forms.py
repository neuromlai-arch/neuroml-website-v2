"""Shared form behaviour: the honeypot trap every public form includes."""

from django import forms


class HoneypotForm(forms.Form):
    """A field named to look real to bots, hidden from humans via CSS
    (see the `.honeypot-field` rule in input.css) rather than `display:none`,
    which some bots already know to skip. Any submission that fills it in is
    spam — rejected with the same validation-error path as a real mistake,
    so there's nothing for a bot to distinguish and retry against.
    """

    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value:
            raise forms.ValidationError("Spam detected.")
        return value
