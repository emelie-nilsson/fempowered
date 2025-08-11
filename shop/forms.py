from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "title": forms.TextInput(attrs={"placeholder": "Title (optional)"}),
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": "Write your review..."}),
        }
