from django import forms
from .models import Review


RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,  
        widget=forms.RadioSelect(attrs={"class": "star-rating"}),
        label="Rating",
        required=True,
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

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        return title.strip() or None  
