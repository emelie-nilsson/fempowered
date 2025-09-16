from django import forms
from .models import ShippingMethod
import re

# Reusable widgets for Bootstrap styling
TEXT = forms.TextInput(attrs={"class": "form-control"})
EMAIL = forms.EmailInput(attrs={"class": "form-control"})
SELECT = forms.Select(attrs={"class": "form-control"})
CHECKBOX = forms.CheckboxInput(attrs={"class": "form-check-input"})


class CheckoutAddressForm(forms.Form):
    # Customer
    full_name = forms.CharField(max_length=120, widget=TEXT, label="Full name")
    email = forms.EmailField(widget=EMAIL, label="Email")
    phone = forms.CharField(max_length=40, required=False, widget=TEXT, label="Phone")

    # Shipping address
    address1 = forms.CharField(max_length=255, widget=TEXT, label="Address")
    address2 = forms.CharField(max_length=255, required=False, widget=TEXT, label="Address line 2")
    postal_code = forms.CharField(max_length=20, widget=TEXT, label="Postal code")
    city = forms.CharField(max_length=80, widget=TEXT, label="City")
    country = forms.CharField(
        max_length=2,
        initial="SE",
        widget=TEXT,
        help_text="ISO-2 country code, e.g. SE",
        label="Country",
    )

    # Shipping method
    shipping_method = forms.ChoiceField(
        choices=ShippingMethod.choices,
        initial=ShippingMethod.STANDARD,
        widget=SELECT,
        label="Shipping method",
    )

    # Billing address
    billing_same_as_shipping = forms.BooleanField(
        initial=True, required=False, widget=CHECKBOX, label="Billing same as shipping"
    )
    billing_address1 = forms.CharField(
        max_length=255, required=False, widget=TEXT, label="Billing address"
    )
    billing_address2 = forms.CharField(
        max_length=255, required=False, widget=TEXT, label="Billing address line 2"
    )
    billing_postal_code = forms.CharField(
        max_length=20, required=False, widget=TEXT, label="Billing postal code"
    )
    billing_city = forms.CharField(max_length=80, required=False, widget=TEXT, label="Billing city")
    billing_country = forms.CharField(
        max_length=2, required=False, widget=TEXT, label="Billing country"
    )

    # Custom validators / normalizers

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if len(name.split()) < 2:
            raise forms.ValidationError("Please enter both first and last name.")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone:
            if not re.match(r"^[0-9+\-\s]+$", phone):
                raise forms.ValidationError("Phone may only contain digits, spaces, + or -.")
            if len(phone) < 7:
                raise forms.ValidationError("Phone number seems too short.")
        return phone

    def clean_postal_code(self):
        code = (self.cleaned_data.get("postal_code") or "").strip()
        if not code.isdigit():
            raise forms.ValidationError("Postal code must contain digits only.")
        if len(code) < 4 or len(code) > 6:
            raise forms.ValidationError("Enter a valid postal code (4–6 digits).")
        return code

    def clean_country(self):
        val = (self.cleaned_data.get("country") or "").strip().upper()
        return val

    def clean_billing_country(self):
        val = (self.cleaned_data.get("billing_country") or "").strip().upper()
        return val

    def clean(self):
        data = super().clean()
        same = data.get("billing_same_as_shipping")
        # If billing is different, require billing fields
        if not same:
            required = (
                "billing_address1",
                "billing_postal_code",
                "billing_city",
                "billing_country",
            )
            for field in required:
                if not (data.get(field) or "").strip():
                    self.add_error(field, "This field is required when billing address differs.")
        return data
