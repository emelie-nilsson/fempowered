from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Name",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Your name"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com"}),
    )
    subject = forms.CharField(
        max_length=120,
        required=False,
        label="Subject",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 6, "placeholder": "How can we help?"}
        ),
    )
    # Honeypot (hidden field)
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_message(self):
        msg = self.cleaned_data["message"].strip()
        if len(msg) < 10:
            raise forms.ValidationError("Please provide a bit more detail (min 10 characters).")
        return msg

    def clean_website(self):
        # If filled -> likely bot
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
