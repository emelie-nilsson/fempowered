from django import forms
from .models import UserAddress

class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = [
            "full_name", "email", "phone",
            "address1", "address2", "postal_code", "city", "country",
            "billing_same_as_shipping",
            "billing_address1", "billing_address2", "billing_postal_code",
            "billing_city", "billing_country",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address1": forms.TextInput(attrs={"class": "form-control"}),
            "address2": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "billing_same_as_shipping": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "billing_address1": forms.TextInput(attrs={"class": "form-control"}),
            "billing_address2": forms.TextInput(attrs={"class": "form-control"}),
            "billing_postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "billing_city": forms.TextInput(attrs={"class": "form-control"}),
            "billing_country": forms.TextInput(attrs={"class": "form-control"}),
        }
