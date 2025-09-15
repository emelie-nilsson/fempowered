from django import forms
from .models import Review

RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]


class ReviewForm(forms.ModelForm):
    # Rating
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect(attrs={"class": "star-rating"}),
        label="Rating",
        required=True,
        error_messages={"required": "Please select a rating."},
    )

    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Title (optional)",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Write your review...",
                }
            ),
        }
        labels = {
            "title": "Title",
            "body": "Review",
        }

    # Title
    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        return title.strip()

    # Body
    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError("Please write a short review.")
        return body

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating not in [1, 2, 3, 4, 5]:
            raise forms.ValidationError("Please select a rating between 1 and 5.")
        return rating
